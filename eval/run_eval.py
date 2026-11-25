"""Evaluation harness on controlled synthetic vocals with known ground truth.

Usage: python eval/run_eval.py [--out docs/experiments/EXP-001-baseline.md]
Measures (separately): melody extraction, key/tempo/downbeat, chord-melody compatibility vs baselines,
arrangement properties, runtime. Objective numbers do NOT replace listening; see docs/EVALUATION.md.
"""
import argparse, itertools, os, sys, time
import numpy as np
sys.path.insert(0, os.path.join(os.path.dirname(__file__), ".."))
from vocal2chord.synth import TUNES, score_to_notes, sing
from vocal2chord.pipeline import analyze_array
from vocal2chord.chords import parse_chord, Chord, best_voicing
from vocal2chord.render import render_guitar

PICKUP = {"twinkle": 0.0, "amazing_grace": 1.0, "ode_to_joy": 0.0}


def note_f1(det, gt, tol=0.05, chroma=True):
    used, tp = set(), 0
    for m, on, _ in gt:
        for j, n in enumerate(det):
            if j in used or abs(n["onset"] - on) > tol:
                continue
            if (n["midi"] % 12 == m % 12) if chroma else (n["midi"] == m):
                used.add(j); tp += 1; break
    p = tp / max(1, len(det)); r = tp / max(1, len(gt))
    return 0.0 if tp == 0 else 2 * p * r / (p + r)


def chord_at(chords, t):
    for c in chords:
        if c["start"] <= t < c["end"]:
            return c["chord"]
    return chords[-1]["chord"]


def strong_notes(gt, bpm, start, bpb, pickup):
    per = 60.0 / bpm
    out = []
    for m, on, d in gt:
        beat = (on - start) / per - pickup
        if d >= 0.9 * per or abs(beat % bpb) < 0.15 or abs(beat % bpb - 2) < 0.15:
            out.append((m, on + d / 2))   # score at the note midpoint (robust to onset jitter at chord boundaries)
    return out


def compat(chords, strong):
    ok = sum(1 for m, t in strong if (m % 12) in parse_chord(chord_at(chords, t)).pcs)
    return ok / max(1, len(strong))


def baseline_chords(arr, tonic, kind):
    """Melody-blind baselines on the SAME grid: tonic-only, or I-V-vi-IV bar loop."""
    bt, bpb = arr["grid"]["beat_times"], arr["grid"]["beats_per_bar"]
    nb = (len(bt) - 1) // bpb
    loop = [(0, "maj"), (7, "maj"), (9, "min"), (5, "maj")] if kind == "loop" else [(0, "maj")]
    out = []
    for b in range(nb):
        r, q = loop[b % len(loop)]
        out.append(dict(start=bt[b * bpb], end=bt[(b + 1) * bpb] if (b + 1) * bpb < len(bt) else 1e9,
                        chord=Chord((tonic + r) % 12, q).name))
    return out


def run_case(name, transpose, bpm, jitter, seed, bpb_override=None):
    tune = TUNES[name]
    gt = score_to_notes(tune, bpm=bpm, transpose=transpose, jitter=jitter, seed=seed)
    y, sr = sing(gt, seed=seed, detune_cents=np.random.default_rng(seed).uniform(-25, 25))
    t0 = time.time()
    arr = analyze_array(y, sr, beats_per_bar=tune["bpb"])
    dt = time.time() - t0
    tonic = (tune["tonic"] + transpose) % 12
    per, bpb = 60.0 / bpm, tune["bpb"]
    start = 0.5
    down = start + PICKUP[name] * per
    ph = ((arr["grid"]["first_downbeat_s"] - down) / (per * bpb)) % 1.0
    strong = strong_notes(gt, bpm, start, bpb, PICKUP[name])
    mine = compat(arr["chords"], strong)
    ev = arr["strums"]
    changes = [c for c in arr["chords"][1:]]
    covered = sum(1 for c in changes if any(abs(e["time"] - c["start"]) < 0.06 and e["gesture"] != "stop" for e in ev))
    return dict(
        case=f"{name}/{transpose:+d}/{int(bpm)}bpm",
        f1_chroma=note_f1(arr["melody"], gt), f1_exact=note_f1(arr["melody"], gt, chroma=False),
        key_ok=arr["key"]["tonic"] == tonic and arr["key"]["mode"] == "major",
        tempo_ok=abs(arr["grid"]["bpm"] - bpm) / bpm < 0.03,
        downbeat_ok=min(ph, 1 - ph) < 0.04,
        downbeat_half=min((ph * 2) % 1.0, 1 - (ph * 2) % 1.0) < 0.04,   # right up to a half-bar (2-beat) shift
        compat=mine, compat_tonic=compat(baseline_chords(arr, tonic, "tonic"), strong),
        compat_loop=compat(baseline_chords(arr, tonic, "loop"), strong),
        n_chords=len(arr["chords"]), changes_per_bar=len(arr["chords"]) / max(1, len(arr["bar_levels"])),
        first_tonic=parse_chord(arr["chords"][0]["chord"]).root == tonic,
        last_tonic=parse_chord(arr["chords"][-1]["chord"]).root == tonic,
        difficulty=float(np.mean([c["voicing"]["difficulty"] for c in arr["chords"]])),
        gestures=len({e["gesture"] for e in ev}), levels=len(set(arr["bar_levels"])),
        change_marked=covered / max(1, len(changes)), secs=dt)


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--out", default=None)
    ap.add_argument("--quick", action="store_true")
    a = ap.parse_args()
    cases = list(itertools.product(TUNES, [0, 3, 6, 9] if a.quick else [0, 2, 5, 7, 9, 11], [80, 100, 120]))
    rows = [run_case(n, t, b, 0.012, i) for i, (n, t, b) in enumerate(cases)]
    g = lambda k: np.mean([r[k] for r in rows])
    lines = ["| metric | value |", "|---|---|"]
    for lab, k, fmt in [("note F1 (pitch-class, onset ±50 ms)", "f1_chroma", "{:.3f}"),
                        ("note F1 (exact MIDI incl. octave)", "f1_exact", "{:.3f}"),
                        ("key correct", "key_ok", "{:.1%}"), ("tempo within 3%", "tempo_ok", "{:.1%}"),
                        ("downbeat phase exact", "downbeat_ok", "{:.1%}"), ("downbeat within a half-bar shift", "downbeat_half", "{:.1%}"),
                        ("strong-note chord-tone rate: vocal2chord", "compat", "{:.3f}"),
                        ("  baseline: tonic only", "compat_tonic", "{:.3f}"),
                        ("  baseline: I-V-vi-IV loop", "compat_loop", "{:.3f}"),
                        ("chords per bar", "changes_per_bar", "{:.2f}"),
                        ("first chord is tonic", "first_tonic", "{:.1%}"), ("last chord is tonic", "last_tonic", "{:.1%}"),
                        ("mean voicing difficulty (0 open .. 2+ barre)", "difficulty", "{:.2f}"),
                        ("distinct gestures used", "gestures", "{:.1f}"), ("distinct intensity levels", "levels", "{:.1f}"),
                        ("chord changes marked by a stroke", "change_marked", "{:.1%}"),
                        ("analysis seconds / song", "secs", "{:.2f}")]:
        lines.append(f"| {lab} | {fmt.format(g(k))} |")
    per_case = ["| case | F1 | key | tempo | dnbt | compat | tonic-only | loop | chords |", "|---|---|---|---|---|---|---|---|---|"]
    for r in rows:
        per_case.append(f"| {r['case']} | {r['f1_chroma']:.2f} | {'Y' if r['key_ok'] else 'N'} | {'Y' if r['tempo_ok'] else 'N'} | "
                        f"{'Y' if r['downbeat_ok'] else 'N'} | {r['compat']:.2f} | {r['compat_tonic']:.2f} | {r['compat_loop']:.2f} | {r['n_chords']} |")
    txt = f"{len(rows)} synthetic cases (tunes x transpositions x tempos, timing jitter 12 ms, detune ±25 cents)\n\n" + \
          "\n".join(lines) + "\n\n<details><summary>per-case</summary>\n\n" + "\n".join(per_case) + "\n\n</details>\n"
    print(txt)
    if a.out:
        open(a.out, "w").write(txt)


if __name__ == "__main__":
    main()
