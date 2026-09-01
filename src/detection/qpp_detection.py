"""Quasi-Periodic Pulsation (QPP) detection on HEL1OS hard X-ray flares.

Pipeline per flare impulsive window ([start, peak]):
  1. detrend the smooth flare envelope (Savitzky-Golay) -> residual
  2. Morlet (complex) wavelet power spectrum for time-localised periods
  3. significance vs a RED-NOISE background using the Vaughan (2005) test:
     fit a power law to the log-periodogram, test peaks against the chi^2_2
     distribution with a GLOBAL (number-of-frequencies-corrected) threshold.

White-noise significance is deliberately NOT used: flare light curves are
red-noise dominated, and a white-noise test would flag the steep low-frequency
continuum as spurious "QPPs". Vaughan (2005) is the standard guard against that.

Reference: Vaughan, S. 2005, A&A 431, 391 -- "A simple test for periodic
signals in red noise spectra".
"""
from __future__ import annotations

from dataclasses import dataclass

import numpy as np
import pywt
from scipy.optimize import minimize
from scipy.signal import savgol_filter
from scipy.stats import norm

WAVELET = "cmor1.5-1.0"        # complex Morlet; central freq 1.0 -> period = scale*dt
# log-chi2_2/2 bias: E[log(chi2_2/2)] = -gamma_Euler = -0.25068
_LOGCHI2_BIAS = 0.25068


@dataclass
class QPP:
    period_s: float
    time_s: float            # time of peak wavelet power (s from window start)
    significance_sigma: float
    global_p: float
    detector: str
    n_cycles: float          # cycles of this period spanned by the window


def detrend_envelope(rate: np.ndarray) -> np.ndarray:
    """Subtract the smooth flare envelope, leaving oscillatory residual.

    Savitzky-Golay with a window ~ half the segment removes variations slower
    than the impulsive rise while preserving sub-window-period oscillations.
    """
    n = len(rate)
    if n < 7:
        return rate - np.nanmean(rate)
    win = max(5, n // 2)
    if win % 2 == 0:
        win += 1
    win = min(win, n if n % 2 == 1 else n - 1)
    poly = min(2, win - 1)
    envelope = savgol_filter(rate, win, poly, mode="interp")
    return rate - envelope


def _whittle_fit(f: np.ndarray, I: np.ndarray):
    """Whittle-likelihood fit of a bending red-noise continuum
    S(f) = A * f^(-beta) + C (power law + white-noise floor). The +C term is
    essential: a pure power law cannot fit AR(1)/bending spectra and leaves the
    high-frequency white floor under-modelled, producing spurious peaks.

    For periodogram ordinates I_j ~ Exp(mean = S_j), the negative log-likelihood
    is sum(I_j / S_j + log S_j). Returns the model S evaluated at f.
    """
    logf = np.log(f)
    # initial guess: power-law slope from a log-log line, floor from high-f median
    b0, a0 = np.polyfit(logf, np.log(I), 1)
    p0 = np.array([a0, max(-b0, 0.0), np.log(np.median(I[-max(3, len(I) // 5):]) + 1e-12)])

    def negloglik(p):
        logA, beta, logC = p
        S = np.exp(logA) * f ** (-beta) + np.exp(logC)
        S = np.clip(S, 1e-30, None)
        return float(np.sum(I / S + np.log(S)))

    res = minimize(negloglik, p0, method="Nelder-Mead",
                   options=dict(maxiter=4000, xatol=1e-4, fatol=1e-4))
    logA, beta, logC = res.x
    S = np.exp(logA) * f ** (-beta) + np.exp(logC)
    return np.clip(S, 1e-30, None), float(beta)


def fourier_rednoise(residual: np.ndarray, dt: float = 1.0):
    """Red-noise periodogram test (Vaughan 2005 framework with a bending
    continuum). Returns frequencies, periods, periodogram, continuum model,
    per-frequency gamma = 2 I / S (~chi^2_2 under H0), the global 95% threshold,
    and a boolean significant mask.
    """
    x = np.asarray(residual, dtype=np.float64)
    x = x - x.mean()
    n = x.size
    freqs = np.fft.rfftfreq(n, d=dt)
    power = (np.abs(np.fft.rfft(x)) ** 2) / n
    sl = slice(1, len(freqs) - 1 if n % 2 == 0 else len(freqs))
    f, I = freqs[sl], power[sl]
    good = (f > 0) & (I > 0)
    f, I = f[good], I[good]
    if f.size < 6:
        return None

    S, beta = _whittle_fit(f, I)                   # mean continuum; I_j ~ Exp(S_j)
    gamma = 2.0 * I / S                            # ~ chi^2_2 under H0

    nfreq = f.size
    g_crit = -2.0 * np.log(1.0 - 0.95 ** (1.0 / nfreq))
    sig = gamma > g_crit
    return dict(freqs=f, periods=1.0 / f, periodogram=I, model=S,
                gamma=gamma, g_crit=g_crit, significant=sig, nfreq=nfreq,
                beta=beta)


def morlet_power(residual: np.ndarray, periods: np.ndarray, dt: float = 1.0):
    """Complex-Morlet wavelet power |W|^2 over the given periods (rows=period)."""
    fc = pywt.central_frequency(WAVELET)
    scales = fc * periods / dt
    coef, _ = pywt.cwt(np.asarray(residual, float), scales, WAVELET, sampling_period=dt)
    return np.abs(coef) ** 2


def _global_sigma(gamma: float, nfreq: int) -> tuple[float, float]:
    """Global p-value and equivalent two-sided Gaussian sigma for a peak."""
    p_local = np.exp(-gamma / 2.0)
    p_global = 1.0 - (1.0 - p_local) ** nfreq
    p_global = min(max(p_global, 1e-300), 1.0)     # floor only to avoid inf
    sigma = float(norm.isf(p_global / 2.0))
    return p_global, sigma


def detect_qpp(
    rate: np.ndarray,
    detector: str,
    dt: float = 1.0,
    min_period_s: float = 4.0,
    max_period_frac: float = 1 / 3,
    max_period_s: float = 300.0,
) -> list[QPP]:
    """Detect QPPs in one flare's impulsive-window count rate for one detector.

    Periods are searched from ``min_period_s`` (>= ~2x the 1 s Nyquist period,
    to avoid Nyquist-edge artefacts) up to ``min(max_period_frac*window,
    max_period_s)``. The 300 s cap keeps the search within the physical QPP
    regime (seconds to ~5 min) and clear of long-window red-noise leakage and
    wavelet edge effects. Returns QPPs passing the Vaughan 95% global test.
    """
    rate = np.asarray(rate, dtype=np.float64)
    rate = rate[np.isfinite(rate)]
    n = rate.size
    if n < 16:
        return []
    window_s = n * dt
    max_period = min(max_period_frac * window_s, max_period_s)
    if max_period <= min_period_s:
        return []

    resid = detrend_envelope(rate)
    fr = fourier_rednoise(resid, dt)
    if fr is None:
        return []

    # candidate significant Fourier periods within the search band
    band = (fr["periods"] >= min_period_s) & (fr["periods"] <= max_period)
    sig_band = fr["significant"] & band
    if not sig_band.any():
        return []

    # wavelet period grid for time-localisation
    wper = np.geomspace(min_period_s, max_period, 48)
    wp = morlet_power(resid, wper, dt)

    out: list[QPP] = []
    # cluster adjacent significant Fourier bins; one QPP per local-max gamma
    idx = np.where(sig_band)[0]
    # split into runs of consecutive indices
    runs = np.split(idx, np.where(np.diff(idx) != 1)[0] + 1)
    for run in runs:
        j = run[np.argmax(fr["gamma"][run])]
        period = float(fr["periods"][j])
        gamma = float(fr["gamma"][j])
        p_global, sigma = _global_sigma(gamma, fr["nfreq"])
        # time of peak wavelet power at the nearest wavelet period row
        prow = int(np.argmin(np.abs(wper - period)))
        tpeak = float(np.argmax(wp[prow]) * dt)
        out.append(QPP(
            period_s=period, time_s=tpeak, significance_sigma=sigma,
            global_p=p_global, detector=detector,
            n_cycles=window_s / period,
        ))
    return out
