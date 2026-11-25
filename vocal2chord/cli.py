"""Command line: arrange | render | demo."""
from __future__ import annotations
import argparse, json, os, sys
import numpy as np
from .audio import load_audio, save_wav
from .pipeline import analyze_array, chord_chart
from .render import render_guitar, mix, write_midi, SR


def _load_beats(path):
    if not path:
        return None
    txt = open(path).read().strip()
    if txt.startswith("["):
        return json.loads(txt)
    return [float(x.split()[0].replace(",", " ")) for x in txt.splitlines() if x.strip()]


def _outputs(arr, vocal, out, guitar_db):
    os.makedirs(out, exist_ok=True)
    json.dump(arr, open(os.path.join(out, "arrangement.json"), "w"), indent=1)
    open(os.path.join(out, "chord_chart.txt"), "w").write(chord_chart(arr) + "\n")
    g, gsr = render_guitar(arr)
    if vocal is not None:
        m, g2 = mix(vocal[0], vocal[1], g, gsr, guitar_db)
        save_wav(os.path.join(out, "mix.wav"), m, gsr)
    save_wav(os.path.join(out, "guitar.wav"), g / max(1e-9, np.abs(g).max()) * 0.9, gsr)
    write_midi(arr, os.path.join(out, "arrangement.mid"))
    print(chord_chart(arr))
    print(f"\nWrote {out}/ : arrangement.json chord_chart.txt guitar.wav mix.wav arrangement.mid")


def main(argv=None):
    ap = argparse.ArgumentParser(prog="vocal2chord", description=__doc__)
    sub = ap.add_subparsers(dest="cmd", required=True)
    a = sub.add_parser("arrange", help="vocal audio -> chords + strumming + audio/MIDI/JSON")
    a.add_argument("vocal")
    a.add_argument("-o", "--out", default="out")
    a.add_argument("--bpm", type=float)
    a.add_argument("--beats", help="beat markers file: JSON list or one time (s) per line; first = downbeat")
    a.add_argument("--beats-per-bar", type=int, default=4)
    a.add_argument("--pickup-beats", type=float, help="beats of pickup before the first downbeat (default: auto)")
    a.add_argument("--key", help="force key, e.g. C, F#m")
    a.add_argument("--guitar-db", type=float, default=-4.0)
    r = sub.add_parser("render", help="re-render an (edited) arrangement.json")
    r.add_argument("arrangement")
    r.add_argument("--vocal")
    r.add_argument("-o", "--out", default="out_edited")
    r.add_argument("--guitar-db", type=float, default=-4.0)
    d = sub.add_parser("demo", help="synthetic-vocal demo (public-domain tunes)")
    d.add_argument("-o", "--out", default="demo_out")
    d.add_argument("--tune", default="twinkle")
    d.add_argument("--transpose", type=int, default=0)
    d.add_argument("--bpm", type=float, default=100.0)
    d.add_argument("--known-grid", action="store_true", help="give the true bpm to the analyser")
    args = ap.parse_args(argv)

    for path in (getattr(args, "vocal", None), getattr(args, "arrangement", None), getattr(args, "beats", None)):
        if path and not os.path.exists(path):
            sys.exit(f"error: file not found: {path}")
    if args.cmd == "arrange":
        y, sr = load_audio(args.vocal)
        arr = analyze_array(y, sr, bpm=args.bpm, beats=_load_beats(args.beats), beats_per_bar=args.beats_per_bar,
                            key=args.key, source=os.path.basename(args.vocal), pickup_beats=args.pickup_beats)
        _outputs(arr, (y, sr), args.out, args.guitar_db)
    elif args.cmd == "render":
        arr = json.load(open(args.arrangement))
        vocal = load_audio(args.vocal) if args.vocal else None
        _outputs(arr, vocal, args.out, args.guitar_db)
    elif args.cmd == "demo":
        from .synth import TUNES, score_to_notes, sing
        tune = TUNES[args.tune]
        gt = score_to_notes(tune, bpm=args.bpm, transpose=args.transpose, jitter=0.01)
        y, sr = sing(gt, detune_cents=10)
        os.makedirs(args.out, exist_ok=True)
        save_wav(os.path.join(args.out, "vocal.wav"), y, sr)
        arr = analyze_array(y, sr, bpm=args.bpm if args.known_grid else None, beats_per_bar=tune["bpb"],
                            source=f"synthetic:{args.tune}")
        _outputs(arr, (y, sr), args.out, -4.0)


if __name__ == "__main__":
    sys.exit(main())
