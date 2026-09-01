"""Export precomputed Morlet wavelet power spectra for a few featured QPP flares
(the X-class headliner + classic-tier examples + one short-tier with the caveat).
Reads the QPP + master catalogs and labeled_seconds; writes dashboard_data/wavelets/.
"""
from __future__ import annotations

import json
import sys
from pathlib import Path

import numpy as np
import pandas as pd

ROOT = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(ROOT))
from src.detection.qpp_detection import detrend_envelope, fourier_rednoise, morlet_power

PROC = ROOT / "data" / "processed"
DET = PROC / "detections"
LBL = PROC / "labeled_seconds"
OUT = ROOT / "dashboard_data" / "wavelets"
CZT_BAND = {"hel1os_czt1": "hel1os_czt1_18_160kev", "hel1os_czt2": "hel1os_czt2_18_160kev"}
CZT_GTI = {"hel1os_czt1": "hel1os_czt1_gti", "hel1os_czt2": "hel1os_czt2_gti"}
TIER_LABEL = {"classic": "classic ≥16 s — robustly solar",
              "intermediate": "intermediate 8–16 s",
              "short": "short 4–8 s — pending instrumental cross-check (Inglis 2011)"}


def pick_featured(qpp: pd.DataFrame) -> pd.DataFrame:
    qpp = qpp.copy()
    qpp["u"] = (pd.to_datetime(qpp["master_peak_utc"]).astype("int64") // 10**9)
    picks = []
    # LEAD: classic >=16s X-class (robustly solar band; gallery ordering per Inglis-caveat policy)
    cx = qpp[(qpp.regime == "classic") & (qpp.goes_class == "X")].sort_values(
        "significance_sigma", ascending=False)
    if len(cx):
        picks.append(("classic_x", cx.iloc[0]))
    xrows = qpp[qpp.goes_class == "X"].sort_values("significance_sigma", ascending=False)
    if len(xrows):
        picks.append(("featured_x", xrows.iloc[0]))
    for i, (_, r) in enumerate(qpp[qpp.regime == "classic"].sort_values("significance_sigma", ascending=False).head(2).iterrows()):
        picks.append((f"classic_{i+1}", r))
    short = qpp[qpp.regime == "short"].sort_values("significance_sigma", ascending=False)
    if len(short):
        picks.append(("short_1", short.iloc[0]))
    return picks


def compute_wavelet(row, master):
    peak_u = int(pd.Timestamp(row["master_peak_utc"]).value // 10**9)
    m = master[np.abs(master["master_peak_unix"] - peak_u) <= 180]
    if not len(m):
        return None
    mr = m.iloc[0]
    start_u, end_u = int(mr["master_start_unix"]), int(mr["master_peak_unix"])
    day = pd.Timestamp(peak_u, unit="s", tz="UTC").strftime("%Y%m%d")
    band, gti = CZT_BAND[row["detector"]], CZT_GTI[row["detector"]]
    df = pd.read_parquet(LBL / f"{day}.parquet", columns=["utc", band, gti])
    u = (df["utc"].astype("int64") // 10**9).to_numpy()
    sel = (u >= start_u) & (u <= end_u) & df[gti].to_numpy(bool)
    rate = df[band].to_numpy(np.float64)[sel]
    rate = rate[np.isfinite(rate)]
    if rate.size < 32:
        return None
    resid = detrend_envelope(rate)
    n = resid.size
    periods = np.geomspace(4, min(n / 3, 300), 48)
    power = morlet_power(resid, periods, dt=1.0)

    # ── display-only derivations from the SAME validated pipeline ────────────
    # Vaughan (2005) red-noise test exactly as used in detection: bending
    # continuum S(f) by Whittle fit + global 95% threshold g_crit. We render the
    # wavelet map in Torrence & Compo (1998) style: power normalised by the
    # fitted red-noise background at each scale, so chi^2_2-distributed under H0
    # and the 95% GLOBAL contour is the single level g_crit/2. One overall
    # calibration constant maps pywt's power normalisation onto the periodogram
    # scale (it cancels in the contour's row-to-row shape — the Vaughan continuum
    # sets that). Detection results are NOT recomputed; catalog values are meta.
    fr = fourier_rednoise(resid, dt=1.0)
    if fr is None:
        return None
    # continuum interpolated (log-log) onto the wavelet period grid
    S_w = np.exp(np.interp(np.log(periods), np.log(fr["periods"][::-1]),
                           np.log(fr["model"][::-1])))
    scale_mean = power.mean(axis=1)
    c = float(np.median(scale_mean / S_w))          # single global calibration
    znorm = power / (c * S_w[:, None])              # units: x red-noise background
    # Contour level for the MAP: local 95% chi^2_2 vs the Vaughan-fitted
    # continuum (Torrence & Compo 1998 convention — standard for wavelet
    # figures). The DETECTION statistic remains the global (nfreq-corrected)
    # Fourier test; its level is exported for reference. chi2.ppf(.95,2)/2.
    sig_level = 2.9957
    sig_global = float(fr["g_crit"] / 2.0)

    # cone of influence (Morlet e-folding: sqrt(2)*scale; cmor fc=1 -> scale=period)
    tt = np.arange(n, dtype=float)
    coi = np.minimum(tt, (n - 1) - tt) / np.sqrt(2.0)
    coi = np.clip(coi, periods[0], None)

    # detected-period band: the significant Fourier run containing the catalog
    # period (fallback +/-10% if the run isn't reproduced in this window cut)
    det_p = float(row["period_s"])
    band_lo, band_hi = det_p * 0.9, det_p * 1.1
    sig_idx = np.where(fr["significant"])[0]
    if sig_idx.size:
        runs = np.split(sig_idx, np.where(np.diff(sig_idx) != 1)[0] + 1)
        for run in runs:
            plo, phi = float(fr["periods"][run].min()), float(fr["periods"][run].max())
            if plo <= det_p <= phi:
                band_lo, band_hi = plo, phi
                break

    # downsample time axis for the browser
    step = max(1, n // 300)
    t = np.arange(0, n, step)
    Z = znorm[:, ::step]
    return dict(t=[int(x) for x in t], periods=[round(float(p), 2) for p in periods],
                znorm=[[round(float(v), 3) for v in rowv] for rowv in Z],
                sig_level=round(sig_level, 3), sig_global=round(sig_global, 3),
                coi=[round(float(v), 2) for v in coi[::step]],
                band_lo=round(band_lo, 2), band_hi=round(band_hi, 2),
                rednoise_beta=round(float(fr["beta"]), 2),
                rate=[round(float(v), 1) for v in rate[::step]])


def main():
    OUT.mkdir(parents=True, exist_ok=True)
    qpp = pd.read_parquet(DET / "qpp_catalog.parquet")
    master = pd.read_parquet(DET / "master_flare_catalog.parquet")
    index = []
    for wid, row in pick_featured(qpp):
        w = compute_wavelet(row, master)
        if w is None:
            print(f"  skip {wid} (no window)"); continue
        meta = dict(id=wid, date=pd.Timestamp(row["master_peak_utc"]).strftime("%Y-%m-%d %H:%M"),
                    detector=row["detector"], period_s=round(float(row["period_s"]), 1),
                    significance=round(float(row["significance_sigma"]), 1),
                    n_cycles=round(float(row["n_cycles"]), 0), regime=row["regime"],
                    tier_label=TIER_LABEL[row["regime"]],
                    goes_class=row["goes_class"] if pd.notna(row["goes_class"]) else None)
        (OUT / f"{wid}.json").write_text(json.dumps({**meta, **w}, allow_nan=False), encoding="utf-8")
        index.append(meta)
        print(f"  wrote {wid}: {meta['date']} {meta['detector']} P={meta['period_s']}s {meta['significance']}sig {meta['regime']}")
    (OUT / "index.json").write_text(json.dumps({"featured": index}, indent=2, allow_nan=False), encoding="utf-8")
    print(f"Wrote {len(index)} wavelets to {OUT}/")


if __name__ == "__main__":
    main()
