"""Beat/bar grid: from supplied markers, a supplied tempo, or estimated from note onsets."""
from __future__ import annotations
from dataclasses import dataclass
import numpy as np


@dataclass
class Grid:
    beats: np.ndarray        # beat times in s; beats[0] is a downbeat
    bpm: float
    beats_per_bar: int
    confidence: float        # 0..1, heuristic
    source: str              # 'markers' | 'bpm' | 'estimated'

    def beat_to_time(self, b):
        b = np.asarray(b, dtype=float)
        idx = np.arange(len(self.beats))
        per = 60.0 / self.bpm
        t = np.interp(b, idx, self.beats)
        t = np.where(b > idx[-1], self.beats[-1] + (b - idx[-1]) * per, t)
        t = np.where(b < 0, self.beats[0] + b * per, t)
        return t if t.ndim else float(t)

    def time_to_beat(self, t):
        t = np.asarray(t, dtype=float)
        idx = np.arange(len(self.beats))
        per = 60.0 / self.bpm
        b = np.interp(t, self.beats, idx)
        b = np.where(t > self.beats[-1], idx[-1] + (t - self.beats[-1]) / per, b)
        b = np.where(t < self.beats[0], (t - self.beats[0]) / per, b)
        return b if b.ndim else float(b)


def _extend(beats, period, bpb, first_onset, end_time):
    beats = list(beats)
    while beats[0] > first_onset + 0.15 * period:      # back-fill whole bars so bar alignment is kept
        beats = [beats[0] - period * (bpb - i) for i in range(bpb)] + beats
    while beats[-1] < end_time + period * bpb:
        beats.append(beats[-1] + period)
    return np.array(beats)


def _onset_weights(notes, phrases):
    starts = {p[0] for p in phrases}
    w = np.array([1.0 + min(n.dur, 1.0) + (1.0 if i in starts else 0.0) for i, n in enumerate(notes)])
    return np.array([n.onset for n in notes]), w


def estimate_grid(notes, phrases, duration, bpm=None, beats=None, beats_per_bar=4) -> Grid:
    first = notes[0].onset if notes else 0.0
    end = max(duration, notes[-1].offset if notes else 0.0)
    if beats is not None and len(beats) >= 2:
        b = np.sort(np.asarray(beats, dtype=float))
        period = float(np.median(np.diff(b)))
        return Grid(_extend(b, period, beats_per_bar, first, end), 60.0 / period, beats_per_bar, 1.0, "markers")
    if not len(notes):
        per = 60.0 / (bpm or 100.0)
        return Grid(_extend([0.0], per, beats_per_bar, 0.0, end), 60.0 / per, beats_per_bar, 0.0, "estimated")
    on, w = _onset_weights(notes, phrases)
    sig = 0.035

    def score(period, phase):
        k = np.round((on - phase) / period)
        d1 = on - (phase + k * period)
        k2 = np.round((on - phase) / (period / 2))
        d2 = on - (phase + k2 * period / 2)
        g = np.maximum(np.exp(-0.5 * (d1 / sig) ** 2), 0.5 * np.exp(-0.5 * (d2 / sig) ** 2))
        return float((w * g).sum())

    if bpm is None:
        cands = np.arange(60, 181, 1.0)
        best, allsc = (-1, None, None), []
        for c in cands:
            p = 60.0 / c
            prior = np.exp(-0.5 * (np.log2(c / 100.0) / 0.6) ** 2)
            for ph in np.linspace(0, p, 40, endpoint=False):
                s = score(p, ph + (first % p)) * prior
                allsc.append(s)
                if s > best[0]:
                    best = (s, c, ph + (first % p))
        _, bpm, phase = best
        for c in np.arange(bpm - 1, bpm + 1.01, 0.25):       # local refinement
            p = 60.0 / c
            for ph in np.linspace(phase - 0.03, phase + 0.03, 25):
                s = score(p, ph)
                if s > score(60.0 / bpm, phase) + 1e-9:
                    bpm, phase = c, ph
        conf = float(np.clip((best[0] - np.mean(allsc)) / (best[0] + 1e-9), 0, 1))
        src = "estimated"
    else:
        p = 60.0 / bpm
        phases = np.linspace(0, p, 60, endpoint=False)
        sc = [score(p, ph) for ph in phases]
        phase = phases[int(np.argmax(sc))]
        conf = float(np.clip((max(sc) - np.mean(sc)) / (max(sc) + 1e-9), 0, 1))
        src = "bpm"
    period = 60.0 / bpm
    # downbeat: choose the rotation whose metrical accents best match long notes, phrase starts, and the final note
    mw = {4: [1.0, 0.25, 0.6, 0.25], 3: [1.0, 0.3, 0.3], 2: [1.0, 0.3]}.get(beats_per_bar, [1.0] + [0.3] * (beats_per_bar - 1))
    starts = {p[0] for p in phrases}
    nb = np.round((on - phase) / period).astype(int)
    dscore = np.zeros(beats_per_bar)
    for i, n in enumerate(notes):
        if abs(on[i] - (phase + nb[i] * period)) >= 0.08:
            continue
        acc = (1.5 * (n.dur >= 1.35 * period) + 1.5 * (i in starts) + 1.5 * (i == len(notes) - 1)
               + 2.0 * (i == 0))   # prior: songs usually start on a downbeat; pickups need contrary evidence (or --pickup-beats)
        for k in range(beats_per_bar):
            dscore[k] += acc * mw[(nb[i] - k) % beats_per_bar]
    down = int(np.argmax(dscore))
    t0 = phase + down * period
    bar = period * beats_per_bar
    t0 -= np.ceil((t0 - (first + 0.15 * period)) / bar) * bar     # bar 0 is the bar holding the first note
    beats_arr = _extend([t0], period, beats_per_bar, first, end)
    return Grid(beats_arr, float(bpm), beats_per_bar, conf, src)
