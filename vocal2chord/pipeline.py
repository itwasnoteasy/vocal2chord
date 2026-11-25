"""End-to-end: vocal audio -> editable arrangement dict (JSON-serialisable)."""
from __future__ import annotations
import time
import numpy as np
from . import __version__
from .audio import load_audio
from .pitch import track_pitch
from .notes import segment_notes, find_phrases
from .grid import estimate_grid
from .harmony import estimate_key, select_progression, KeyCand, PC
from .arrange import plan
from .chords import best_voicing, parse_chord

SCHEMA_VERSION = 1


def analyze_array(y, sr, bpm=None, beats=None, beats_per_bar=4, key=None, source="array", pickup_beats=None):
    t0 = time.time()
    track = track_pitch(y, sr)
    notes = segment_notes(track)
    if not notes:
        raise ValueError("No sung pitch detected in the audio.")
    phrases = find_phrases(notes)
    duration = len(y) / sr
    grid = estimate_grid(notes, phrases, duration, bpm=bpm, beats=beats, beats_per_bar=beats_per_bar)
    if pickup_beats is not None and grid.source != "markers":
        # user states how many beats precede the first downbeat: re-anchor bar 0 so the first note sits at that beat
        first = notes[0].onset
        period = 60.0 / grid.bpm
        t_down = first + pickup_beats * period
        bar = period * beats_per_bar
        t0b = t_down - np.ceil((t_down - (first + 0.15 * period)) / bar) * bar
        n = int((duration + bar * 2 - t0b) / period) + 1
        grid.beats = t0b + period * np.arange(n)
    keys = estimate_key(notes)
    if key:
        ton = PC.index(key.rstrip("m"))
        keys = [KeyCand(ton, "minor" if key.endswith("m") else "major", 1.0)]
    key_sel, events = select_progression(grid, notes, phrases, keys)
    strums, levels = plan(grid, notes, phrases, events, track, key_sel)
    bpb = grid.beats_per_bar
    chords = []
    for e in events:
        v = best_voicing(e.chord)
        chords.append(dict(
            start=round(float(grid.beat_to_time(e.start_beat)), 4), end=round(float(grid.beat_to_time(e.end_beat)), 4),
            bar=int(e.start_beat // bpb) + 1, beat_in_bar=round(e.start_beat % bpb + 1, 2),
            chord=e.chord.name, function=e.function, confidence=e.confidence, melody_coverage=e.coverage,
            voicing=dict(frets=list(v.frets), difficulty=round(v.difficulty, 2)), alternatives=e.alternatives))
    arr = dict(
        schema_version=SCHEMA_VERSION,
        meta=dict(tool="vocal2chord", version=__version__, source=source, duration_s=round(duration, 3),
                  analysis_seconds=round(time.time() - t0, 2),
                  notes="Edit 'chords' (names) and 'strums' (gesture/time/dir/velocity), then run `render`. "
                        "Strum chord names are re-derived from the chord timeline at render time."),
        grid=dict(bpm=round(grid.bpm, 2), beats_per_bar=bpb, confidence=round(grid.confidence, 2), source=grid.source,
                  first_downbeat_s=round(float(grid.beats[0]), 4), beat_times=[round(float(b), 4) for b in grid.beats]),
        key=dict(name=key_sel.name, tonic=key_sel.tonic, mode=key_sel.mode, score=round(key_sel.score, 3),
                 candidates=[dict(name=k.name, score=round(k.score, 3)) for k in keys]),
        phrases=[dict(start=round(notes[s].onset, 3), end=round(notes[e - 1].offset, 3)) for s, e in phrases],
        melody=[n.to_dict() for n in notes],
        bar_levels=[int(x) for x in levels],
        chords=chords,
        strums=strums,
    )
    return arr


def analyze(path, **kw):
    y, sr = load_audio(path)
    return analyze_array(y, sr, source=str(path), **kw), (y, sr)


def chord_chart(arr) -> str:
    """Human-readable bar-by-bar chart with alternatives."""
    bpb = arr["grid"]["beats_per_bar"]
    lines = [f"Key: {arr['key']['name']}   Tempo: {arr['grid']['bpm']} bpm ({arr['grid']['source']}, "
             f"grid confidence {arr['grid']['confidence']})   {bpb}/4",
             f"Key candidates: " + ", ".join(f"{k['name']} ({k['score']})" for k in arr["key"]["candidates"]), ""]
    for c in arr["chords"]:
        alts = "; ".join(f"{a['chord']} [{a['kind']}, d={a['delta']:+.1f}]" for a in c["alternatives"][:3])
        fn = parse_chord(c["chord"]).roman(arr["key"]["tonic"])      # recomputed so edited chords are labelled correctly
        lines.append(f"bar {c['bar']:>3} beat {c['beat_in_bar']:<4} {c['chord']:<7} {fn:<5} "
                     f"conf {c['confidence']:.2f}  alts: {alts}")
    g = {}
    for s in arr["strums"]:
        g[s["gesture"]] = g.get(s["gesture"], 0) + 1
    lines += ["", "Gestures used: " + ", ".join(f"{k}={v}" for k, v in sorted(g.items())),
              "Bar intensity (0-3): " + " ".join(map(str, arr["bar_levels"]))]
    return "\n".join(lines)
