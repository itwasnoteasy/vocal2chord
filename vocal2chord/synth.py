"""Synthetic 'sung' vocal for demos and controlled tests (harmonic source, vibrato, formants, syllable dips).

This is NOT a substitute for real voices; it gives ground-truth notes for unit tests and a reproducible demo.
"""
from __future__ import annotations
import numpy as np
from scipy.signal import lfilter

# Public-domain tunes as (midi_offset_from_tonic, beats); None offset = rest. Approximate transcriptions.
TUNES = {
    "twinkle": dict(bpb=4, tonic=60, notes=[
        (0, 1), (0, 1), (7, 1), (7, 1), (9, 1), (9, 1), (7, 1.5), (None, .5),
        (5, 1), (5, 1), (4, 1), (4, 1), (2, 1), (2, 1), (0, 1.5), (None, .5),
        (7, 1), (7, 1), (5, 1), (5, 1), (4, 1), (4, 1), (2, 1.5), (None, .5),
        (7, 1), (7, 1), (5, 1), (5, 1), (4, 1), (4, 1), (2, 1.5), (None, .5),
        (0, 1), (0, 1), (7, 1), (7, 1), (9, 1), (9, 1), (7, 1.5), (None, .5),
        (5, 1), (5, 1), (4, 1), (4, 1), (2, 1), (2, 1), (0, 4)]),
    "amazing_grace": dict(bpb=3, tonic=67, notes=[   # pickup is one beat; grid starts on the first full bar
        (-5, 1), (0, 2), (4, .5), (0, .5), (4, 2), (2, 1), (0, 2), (-3, 1), (-5, 2.5), (None, .5),
        (-5, 1), (0, 2), (4, .5), (0, .5), (4, 2), (7, 1), (9, 2.5), (None, .5),
        (9, 1), (7, 2), (4, .5), (0, .5), (4, 2), (2, 1), (0, 2), (-3, 1), (-5, 2.5), (None, .5),
        (-5, 1), (0, 2), (4, .5), (0, .5), (4, 2), (2, 1), (0, 3)]),
    "ode_to_joy": dict(bpb=4, tonic=62, notes=[
        (4, 1), (4, 1), (5, 1), (7, 1), (7, 1), (5, 1), (4, 1), (2, 1),
        (0, 1), (0, 1), (2, 1), (4, 1), (4, 1.5), (2, .5), (2, 2),
        (4, 1), (4, 1), (5, 1), (7, 1), (7, 1), (5, 1), (4, 1), (2, 1),
        (0, 1), (0, 1), (2, 1), (4, 1), (2, 1.5), (0, .5), (0, 2)]),
}

SR = 22050


def score_to_notes(tune, bpm=100.0, transpose=0, start=0.5, jitter=0.0, seed=0, breath=0.0):
    """-> list of (midi, onset_s, dur_s). Ground truth for tests."""
    rng = np.random.default_rng(seed)
    per = 60.0 / bpm
    t, out = start, []
    for off, beats in tune["notes"]:
        if off is not None:
            on = t + rng.normal(0, jitter)
            out.append((tune["tonic"] + off + transpose, on, beats * per * 0.97))
        t += beats * per
    return out


def sing(notes, sr=SR, tail=1.0, seed=0, vibrato_cents=30.0, detune_cents=0.0, vowel=((700, 90), (1200, 110))):
    rng = np.random.default_rng(seed)
    total = max(o + d for _, o, d in notes) + tail
    n = int(total * sr)
    f0 = np.zeros(n)
    amp = np.zeros(n)
    t = np.arange(n) / sr
    cur = None
    for m, on, dur in notes:
        a, b = int(on * sr), min(n, int((on + dur) * sr))
        f = 440.0 * 2 ** ((m - 69 + detune_cents / 100) / 12)
        seg_t = t[a:b] - on
        vib = 1 + (vibrato_cents / 1200 * np.log(2)) * np.sin(2 * np.pi * 5.5 * seg_t) * np.clip(seg_t / 0.25, 0, 1)
        f0[a:b] = f * vib
        env = np.clip(seg_t / 0.03, 0, 1) * np.clip((dur - seg_t) / 0.05, 0, 1)
        env = env * (1 - 0.85 * np.exp(-0.5 * (seg_t / 0.02) ** 2))        # consonant dip at syllable start
        amp[a:b] = env * (0.6 + 0.4 * np.clip(seg_t / 0.12, 0, 1))
        if cur is not None and a > 0:   # short glide from previous pitch
            g = min(b, a + int(0.04 * sr)) - a
            if g > 0:
                f0[a:a + g] = np.linspace(cur, f0[a + g - 1], g)
        cur = f
    f0 = np.where(f0 > 0, f0, 100.0)
    phase = 2 * np.pi * np.cumsum(f0) / sr
    sig = np.zeros(n)
    for h in range(1, 40):
        fh = f0 * h
        formant = sum(np.exp(-0.5 * ((fh - fc) / bw) ** 2) for fc, bw in vowel) + 0.15 / h
        sig += formant * np.sin(h * phase + rng.uniform(0, 6.28)) * (fh < sr / 2 - 500)
    sig += 0.02 * rng.normal(size=n) * amp.max()
    sig = lfilter([1], [1, -0.6], sig) * amp
    sig = lfilter([1, -0.97], [1], sig) * 0 + sig   # keep dynamic; no pre-emphasis
    return (0.8 * sig / max(1e-9, np.abs(sig).max())).astype(np.float32), sr
