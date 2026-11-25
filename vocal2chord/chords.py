"""Chord vocabulary, naming/parsing, and guitar voicings (open shapes + movable E/A barre shapes)."""
from __future__ import annotations
import re
from dataclasses import dataclass

QUALITIES = {
    "maj": (0, 4, 7), "min": (0, 3, 7), "7": (0, 4, 7, 10), "maj7": (0, 4, 7, 11), "m7": (0, 3, 7, 10),
    "sus2": (0, 2, 7), "sus4": (0, 5, 7), "add9": (0, 4, 7, 2), "dim": (0, 3, 6),
}
SUFFIX = {"maj": "", "min": "m", "7": "7", "maj7": "maj7", "m7": "m7", "sus2": "sus2", "sus4": "sus4",
          "add9": "add9", "dim": "dim"}
_FROM_SUFFIX = {v: k for k, v in SUFFIX.items()}
_FROM_SUFFIX.update({"min": "min", "-": "min", "M": "maj", "M7": "maj7", "mi": "min", "m9": "m7", "9": "7"})
FLAT_NAMES = ["C", "Db", "D", "Eb", "E", "F", "F#", "G", "Ab", "A", "Bb", "B"]
_NOTE_PC = {"C": 0, "D": 2, "E": 4, "F": 5, "G": 7, "A": 9, "B": 11}
MINORISH = {"min", "m7", "dim"}
ROMAN = ["I", "bII", "II", "bIII", "III", "IV", "#IV", "V", "bVI", "VI", "bVII", "VII"]
STRING_MIDI = [40, 45, 50, 55, 59, 64]  # E2 A2 D3 G3 B3 E4


@dataclass(frozen=True)
class Chord:
    root: int
    quality: str = "maj"

    @property
    def name(self) -> str:
        r = self.root % 12
        if self.quality in MINORISH and r in (1, 6, 8):
            n = {1: "C#", 6: "F#", 8: "G#"}[r]
        else:
            n = FLAT_NAMES[r]
        return n + SUFFIX[self.quality]

    @property
    def pcs(self) -> frozenset:
        return frozenset((self.root + i) % 12 for i in QUALITIES[self.quality])

    @property
    def core(self) -> frozenset:
        return frozenset((self.root + i) % 12 for i in QUALITIES[self.quality][:3])

    def roman(self, tonic: int) -> str:
        r = ROMAN[(self.root - tonic) % 12]
        return r.lower() if self.quality in MINORISH else r


def parse_chord(name: str) -> Chord:
    m = re.match(r"^([A-G])([#b]?)(.*)$", name.strip())
    if not m or m.group(3) not in _FROM_SUFFIX:
        raise ValueError(f"unrecognised chord: {name!r}")
    pc = _NOTE_PC[m.group(1)] + {"#": 1, "b": -1, "": 0}[m.group(2)]
    return Chord(pc % 12, _FROM_SUFFIX[m.group(3)])


# ---- voicings: 6 entries low E -> high E, None = not played -------------------------------------
_X = None
OPEN = {
    "C": [_X, 3, 2, 0, 1, 0], "Cmaj7": [_X, 3, 2, 0, 0, 0], "Cadd9": [_X, 3, 2, 0, 3, 0], "C7": [_X, 3, 2, 3, 1, 0],
    "D": [_X, _X, 0, 2, 3, 2], "Dm": [_X, _X, 0, 2, 3, 1], "D7": [_X, _X, 0, 2, 1, 2], "Dmaj7": [_X, _X, 0, 2, 2, 2],
    "Dm7": [_X, _X, 0, 2, 1, 1], "Dsus2": [_X, _X, 0, 2, 3, 0], "Dsus4": [_X, _X, 0, 2, 3, 3],
    "E": [0, 2, 2, 1, 0, 0], "Em": [0, 2, 2, 0, 0, 0], "E7": [0, 2, 0, 1, 0, 0], "Emaj7": [0, 2, 1, 1, 0, 0],
    "Em7": [0, 2, 0, 0, 0, 0], "Esus4": [0, 2, 2, 2, 0, 0],
    "F": [1, 3, 3, 2, 1, 1], "Fmaj7": [_X, _X, 3, 2, 1, 0],
    "G": [3, 2, 0, 0, 0, 3], "G7": [3, 2, 0, 0, 0, 1], "Gmaj7": [3, 2, 0, 0, 0, 2], "Gsus4": [3, 3, 0, 0, 1, 3],
    "A": [_X, 0, 2, 2, 2, 0], "Am": [_X, 0, 2, 2, 1, 0], "A7": [_X, 0, 2, 0, 2, 0], "Amaj7": [_X, 0, 2, 1, 2, 0],
    "Am7": [_X, 0, 2, 0, 1, 0], "Asus2": [_X, 0, 2, 2, 0, 0], "Asus4": [_X, 0, 2, 2, 3, 0],
    "B7": [_X, 2, 1, 2, 0, 2],
}
OPEN_DIFFICULTY = {"F": 2.0, "Fmaj7": 1.0, "Gsus4": 1.0, "G7": 0.5, "C7": 0.8, "B7": 1.0}
E_SHAPE = {"maj": [0, 2, 2, 1, 0, 0], "min": [0, 2, 2, 0, 0, 0], "7": [0, 2, 0, 1, 0, 0], "maj7": [0, 2, 1, 1, 0, 0],
           "m7": [0, 2, 0, 0, 0, 0], "sus4": [0, 2, 2, 2, 0, 0]}
A_SHAPE = {"maj": [_X, 0, 2, 2, 2, 0], "min": [_X, 0, 2, 2, 1, 0], "7": [_X, 0, 2, 0, 2, 0],
           "maj7": [_X, 0, 2, 1, 2, 0], "m7": [_X, 0, 2, 0, 1, 0], "sus2": [_X, 0, 2, 2, 0, 0],
           "sus4": [_X, 0, 2, 2, 3, 0], "add9": [_X, 0, 2, 4, 2, 0], "dim": [_X, 0, 1, 2, 1, _X]}


@dataclass(frozen=True)
class Voicing:
    frets: tuple
    difficulty: float

    @property
    def strings(self):
        return [i for i, f in enumerate(self.frets) if f is not None]

    @property
    def midi(self):
        return [STRING_MIDI[i] + self.frets[i] for i in self.strings]


_cache: dict = {}


def best_voicing(chord: Chord) -> Voicing:
    """Easiest voicing: open library first, else lowest-position E/A-shape barre chord."""
    if chord in _cache:
        return _cache[chord]
    cands = []
    nm = chord.name
    if nm in OPEN:
        cands.append(Voicing(tuple(OPEN[nm]), OPEN_DIFFICULTY.get(nm, 0.0)))
    for shape, base in ((E_SHAPE, 4), (A_SHAPE, 9)):
        if chord.quality in shape:
            f = (chord.root - base) % 12
            fr = tuple(None if o is None else o + f for o in shape[chord.quality])
            cands.append(Voicing(fr, 0.0 if f == 0 else 1.5 + 0.08 * f + (0.0 if shape is E_SHAPE else 0.2)))
    if not cands:  # no shape for this quality (e.g. Esus2): fall back to the plain triad
        v = best_voicing(Chord(chord.root, "min" if chord.quality in MINORISH else "maj"))
        cands.append(v)
    v = min(cands, key=lambda c: c.difficulty)
    _cache[chord] = v
    return v
