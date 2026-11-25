"""Pitch track -> note events and phrases."""
from __future__ import annotations
from dataclasses import dataclass, asdict
import numpy as np
from scipy.signal import find_peaks
from .pitch import PitchTrack, _runs


@dataclass
class Note:
    onset: float
    offset: float
    midi: int        # nearest semitone (octave may be wrong; harmony uses pitch class only)
    pitch: float     # mean fractional midi
    rms: float

    @property
    def dur(self):
        return self.offset - self.onset

    def to_dict(self):
        d = asdict(self)
        return {k: (round(v, 4) if isinstance(v, float) else v) for k, v in d.items()}


def _hysteresis(m, hold=4, tol=0.75):
    """Split a run into (start, end) index pairs of stable pitch."""
    segs, start, cur = [], 0, float(np.round(m[0]))
    cand, cand_n = None, 0
    for i in range(1, len(m)):
        if abs(m[i] - cur) < tol:
            cand, cand_n = None, 0
            continue
        r = float(np.round(m[i]))
        if cand == r:
            cand_n += 1
        else:
            cand, cand_n = r, 1
        if cand_n >= hold:
            cut = i - cand_n + 1
            segs.append((start, cut))
            start, cur, cand, cand_n = cut, r, None, 0
    segs.append((start, len(m)))
    return segs


def segment_notes(tr: PitchTrack, min_dur=0.07) -> list[Note]:
    notes: list[Note] = []
    db = 20 * np.log10(np.maximum(tr.rms, 1e-9))
    for a, b in _runs(~np.isnan(tr.midi)):
        m = tr.midi[a:b]
        for s, e in _hysteresis(m):
            # split on clear energy dips (re-articulated repeated notes / syllables)
            seg_db = np.convolve(db[a + s:a + e], np.ones(3) / 3, mode="same")
            cuts = [0, e - s]
            if e - s >= 8:
                pk, _ = find_peaks(-seg_db, prominence=6.0)
                cuts = [0] + [int(p) for p in pk if 3 <= p <= e - s - 3] + [e - s]
            for c0, c1 in zip(cuts[:-1], cuts[1:]):
                i0, i1 = a + s + c0, a + s + c1
                if (i1 - i0) * tr.hop < min_dur:
                    continue
                p = float(np.median(tr.midi[i0:i1]))
                notes.append(Note(float(tr.times[i0]), float(tr.times[i1 - 1] + tr.hop), int(round(p)),
                                  p, float(np.mean(tr.rms[i0:i1]))))
    return _merge_octave_fragments(notes)


def _merge_octave_fragments(notes, max_frag=0.25, max_gap=0.06):
    """A short note contiguous with the previous one and the same pitch class is an octave-tracking glitch."""
    out: list[Note] = []
    for n in notes:
        if (out and n.dur < max_frag and n.onset - out[-1].offset < max_gap
                and n.midi % 12 == out[-1].midi % 12):
            out[-1].offset = n.offset
            continue
        out.append(n)
    return out


def find_phrases(notes: list[Note], gap=0.22) -> list[tuple[int, int]]:
    """Phrase = run of notes separated by < gap seconds. Returns (first, last+1) note indices."""
    if not notes:
        return []
    out, s = [], 0
    for i in range(1, len(notes)):
        if notes[i].onset - notes[i - 1].offset >= gap:
            out.append((s, i))
            s = i
    out.append((s, len(notes)))
    return out
