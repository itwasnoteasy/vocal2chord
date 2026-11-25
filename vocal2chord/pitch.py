"""Monophonic pitch tracking (YIN, de Cheveigne & Kawahara 2002) in plain numpy.

Chosen over pYIN/CREPE for the MVP: no heavy dependencies, deterministic, fast.
Octave errors are corrected per voiced run by continuity (see docs/decisions/0001).
"""
from __future__ import annotations
from dataclasses import dataclass
import numpy as np
from scipy.ndimage import median_filter
from .audio import resample

TSR = 16000


@dataclass
class PitchTrack:
    times: np.ndarray   # s
    midi: np.ndarray    # float midi, nan where unvoiced
    conf: np.ndarray    # 0..1
    rms: np.ndarray     # linear RMS of the frame
    hop: float


def track_pitch(y, sr, hop=0.01, fmin=70.0, fmax=900.0, thr=0.15, floor_db=-42.0) -> PitchTrack:
    x = resample(np.asarray(y, dtype=np.float32), sr, TSR).astype(np.float64)
    hop_n = int(round(TSR * hop))
    W = 640
    tau_max = int(TSR / fmin) + 1
    tau_min = max(2, int(TSR / fmax))
    L = W + tau_max + 2
    xp = np.pad(x, (L, L + hop_n))
    n_frames = int(len(x) / hop_n) + 1
    nfft = 1 << int(np.ceil(np.log2(L + W)))
    midi = np.full(n_frames, np.nan)
    conf = np.zeros(n_frames)
    rms = np.zeros(n_frames)
    taus = np.arange(tau_max + 1)
    for i in range(n_frames):
        s = L + i * hop_n - W // 2
        seg = xp[s:s + L]
        a = seg[:W]
        e0 = float(a @ a)
        rms[i] = np.sqrt(e0 / W)
        if e0 < 1e-10:
            continue
        r = np.fft.irfft(np.conj(np.fft.rfft(a, nfft)) * np.fft.rfft(seg, nfft), nfft)[:tau_max + 1]
        c = np.concatenate([[0.0], np.cumsum(seg * seg)])
        et = c[taus + W] - c[taus]
        d = e0 + et - 2 * r
        d[0] = 0.0
        cs = np.cumsum(d[1:])
        cmnd = np.ones(tau_max + 1)
        cmnd[1:] = d[1:] * taus[1:] / np.maximum(cs, 1e-12)
        seg_c = cmnd[tau_min:tau_max]
        below = np.where(seg_c < thr)[0]
        if below.size:
            k = below[0]
            while k + 1 < seg_c.size and seg_c[k + 1] < seg_c[k]:
                k += 1
        else:
            k = int(np.argmin(seg_c))
        tau = k + tau_min
        v = cmnd[tau]
        if 1 <= tau < tau_max:  # parabolic refinement
            a0, b0, c0 = cmnd[tau - 1], cmnd[tau], cmnd[tau + 1]
            den = a0 - 2 * b0 + c0
            if abs(den) > 1e-12:
                tau = tau + 0.5 * (a0 - c0) / den
        conf[i] = max(0.0, 1.0 - v)
        if v < 0.3:
            midi[i] = 69 + 12 * np.log2((TSR / tau) / 440.0)
    peak = max(rms.max(), 1e-9)
    db = 20 * np.log10(np.maximum(rms, 1e-9) / peak)
    midi[db < floor_db] = np.nan
    midi = _clean(midi)
    times = np.arange(n_frames) * hop
    return PitchTrack(times, midi, conf, rms, hop)


def _runs(mask):
    idx = np.flatnonzero(mask)
    if idx.size == 0:
        return []
    splits = np.where(np.diff(idx) > 1)[0] + 1
    return [(g[0], g[-1] + 1) for g in np.split(idx, splits)]


def _clean(midi, min_frames=5):
    """Drop tiny voiced islands, fix octave jumps within a run, median-smooth."""
    midi = midi.copy()
    for a, b in _runs(~np.isnan(midi)):
        if b - a < min_frames:
            midi[a:b] = np.nan
            continue
        m = midi[a:b]
        # octave continuity vs. the local (~0.6 s) median pitch: fold frames that are clearly an octave off
        for _ in range(2):
            loc = median_filter(m, size=min(61, 2 * (len(m) // 2) - 1) or 1, mode="nearest")
            up = np.abs(m - 12 - loc) + 3.0 < np.abs(m - loc)
            dn = np.abs(m + 12 - loc) + 3.0 < np.abs(m - loc)
            m = np.where(up, m - 12, np.where(dn, m + 12, m))
        midi[a:b] = median_filter(m, size=5, mode="nearest")
    return midi
