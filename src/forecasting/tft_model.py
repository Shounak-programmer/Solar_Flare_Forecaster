"""Compact Temporal Fusion Transformer for multi-horizon flare forecasting.

From-scratch (no pytorch-forecasting dependency; gives control over the single
CPU-bound run budget and lets us implement the requested adaptations):
  - TFT-style variable-selection gating over time-varying + static features
  - Alshammari encoder block: LayerNorm -> multi-head self-attention -> residual
    -> Conv1D over time -> residual -> mean+max temporal pooling
  - SolarFlareNet-style multi-output: independent heads per horizon (15/30/60)
  - focal loss for class imbalance (NOT plain BCE)
  - MC-dropout at inference for an uncertainty interval (the quantile/uncertainty
    story; probability calibration itself is handled by isotonic regression in 4d)

Input: trailing L-minute sequence of time-varying features + static covariates.
All inputs are <= t (leakage-safe; sequences never cross a day/GTI boundary).
"""
from __future__ import annotations

import numpy as np
import torch
import torch.nn as nn
import torch.nn.functional as F


class VariableSelection(nn.Module):
    """Learned softmax gating over input features (simplified TFT VSN)."""

    def __init__(self, n_features: int):
        super().__init__()
        self.gate = nn.Sequential(nn.Linear(n_features, n_features), nn.ReLU(),
                                  nn.Linear(n_features, n_features))

    def forward(self, x):                      # x: [..., F]
        w = torch.softmax(self.gate(x), dim=-1)
        return x * w, w


class EncoderBlock(nn.Module):
    """Alshammari-style: LN -> MHA -> residual -> Conv1D -> residual."""

    def __init__(self, d_model: int, n_heads: int, dropout: float):
        super().__init__()
        self.ln1 = nn.LayerNorm(d_model)
        self.attn = nn.MultiheadAttention(d_model, n_heads, dropout=dropout,
                                          batch_first=True)
        self.ln2 = nn.LayerNorm(d_model)
        self.conv = nn.Conv1d(d_model, d_model, kernel_size=3, padding=1)
        self.drop = nn.Dropout(dropout)

    def forward(self, x):                       # x: [B, L, D]
        h = self.ln1(x)
        a, _ = self.attn(h, h, h, need_weights=False)
        x = x + self.drop(a)
        h = self.ln2(x).transpose(1, 2)         # [B, D, L]
        c = F.gelu(self.conv(h)).transpose(1, 2)
        return x + self.drop(c)


class FlareTFT(nn.Module):
    def __init__(self, n_tv: int, n_static: int, n_horizons: int = 3,
                 d_model: int = 48, n_heads: int = 4, dropout: float = 0.2):
        super().__init__()
        self.vsn_tv = VariableSelection(n_tv)
        self.vsn_st = VariableSelection(n_static) if n_static else None
        self.tv_proj = nn.Linear(n_tv, d_model)
        self.st_proj = nn.Linear(n_static, d_model) if n_static else None
        self.encoder = EncoderBlock(d_model, n_heads, dropout)
        self.drop = nn.Dropout(dropout)
        self.head = nn.Sequential(nn.Linear(2 * d_model, d_model), nn.GELU(),
                                  nn.Dropout(dropout))
        self.out = nn.Linear(d_model, n_horizons)
        self._last_vsn = None

    def forward(self, x_seq, x_static):
        xs, w_tv = self.vsn_tv(x_seq)           # [B, L, n_tv]
        self._last_vsn = w_tv.mean(dim=(0, 1)).detach()
        h = self.tv_proj(xs)                    # [B, L, D]
        if self.st_proj is not None:
            st, _ = self.vsn_st(x_static)
            h = h + self.st_proj(st).unsqueeze(1)
        h = self.encoder(h)
        pooled = torch.cat([h.mean(dim=1), h.amax(dim=1)], dim=-1)
        return self.out(self.head(self.drop(pooled)))   # logits [B, n_horizons]


def focal_loss(logits, targets, alpha=0.75, gamma=2.0):
    """Multi-horizon focal loss (sum over horizons)."""
    p = torch.sigmoid(logits)
    ce = F.binary_cross_entropy_with_logits(logits, targets, reduction="none")
    p_t = p * targets + (1 - p) * (1 - targets)
    a_t = alpha * targets + (1 - alpha) * (1 - targets)
    return (a_t * (1 - p_t) ** gamma * ce).mean()


# ---------------------------------------------------------------------------
# Sequence dataset: slices trailing L-minute windows from per-split arrays.
# ---------------------------------------------------------------------------
class SequenceDataset(torch.utils.data.Dataset):
    def __init__(self, feats_tv, feats_st, targets, valid_idx, lookback):
        self.tv = feats_tv                      # [N, n_tv] float32 (ordered)
        self.st = feats_st                      # [N, n_static]
        self.y = targets                        # [N, n_horizons]
        self.idx = valid_idx                    # end-of-window positions
        self.L = lookback

    def __len__(self):
        return len(self.idx)

    def __getitem__(self, j):
        i = self.idx[j]
        seq = self.tv[i - self.L + 1: i + 1]
        return (torch.from_numpy(seq), torch.from_numpy(self.st[i]),
                torch.from_numpy(self.y[i]))


@torch.no_grad()
def predict_proba(model, loader, n_horizons, device, mc_samples: int = 0,
                  amp_dtype=None):
    """Return probabilities [N, n_horizons]. mc_samples>0 enables MC-dropout
    and also returns the std (uncertainty) across stochastic passes."""
    model.eval()
    if mc_samples > 0:
        for m in model.modules():
            if isinstance(m, nn.Dropout):
                m.train()
    dt = device.type if hasattr(device, "type") else str(device)
    use_amp = (dt == "cuda") and (amp_dtype is not None)
    outs = []
    for xb, sb, _ in loader:
        xb, sb = xb.to(device, non_blocking=True), sb.to(device, non_blocking=True)
        with torch.autocast(device_type=dt, dtype=amp_dtype, enabled=use_amp):
            if mc_samples > 0:
                ps = torch.stack([torch.sigmoid(model(xb, sb)).float()
                                  for _ in range(mc_samples)])
                outs.append((ps.mean(0).cpu(), ps.std(0).cpu()))
            else:
                outs.append((torch.sigmoid(model(xb, sb)).float().cpu(), None))
    probs = torch.cat([o[0] for o in outs]).numpy()
    if mc_samples > 0:
        std = torch.cat([o[1] for o in outs]).numpy()
        return probs, std
    return probs, None
