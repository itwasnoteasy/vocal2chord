# vocal2chord

Give it a **solo vocal recording**; get a **chord progression with alternatives** and a **dynamic rhythm-guitar arrangement**
(strums, held chords, single bass notes, mutes, pickups, stops at breaths, an ending), rendered against your vocal and exported as
editable JSON + MIDI. It harmonises *your* melody — no song identification, any key, your own timing. Everything runs locally.

## Setup
```bash
pip install -r requirements.txt        # numpy scipy soundfile mido (+ ffmpeg on PATH for mp3/m4a input)
python -m pytest -q                    # 23 tests, ~13 s
```

## Try it (no recording needed)
```bash
python -m vocal2chord demo -o demo_out --tune twinkle      # also: amazing_grace, ode_to_joy; --transpose 3 --bpm 90
```
Pre-generated results are in `examples/<tune>/` (`mix.mp3` = synthetic vocal + guitar, `arrangement.json`, `chord_chart.txt`, `arrangement.mid`).

## Your vocal
```bash
python -m vocal2chord arrange my_vocal.wav -o out/my_vocal                  # fully automatic
python -m vocal2chord arrange my_vocal.wav --bpm 92 --beats-per-bar 3 --pickup-beats 1 --key Am -o out/my_vocal
python -m vocal2chord arrange my_vocal.wav --beats my_vocal.beats.txt -o out/my_vocal   # first marker = downbeat
```
Outputs in `out/my_vocal/`: `mix.wav` (vocal+guitar), `guitar.wav`, `arrangement.mid`, `arrangement.json` (editable), `chord_chart.txt`.

## Edit and re-audition
Edit `arrangement.json` — change a chord name (pick from its `alternatives`), or tweak `strums` — then:
```bash
python -m vocal2chord render out/my_vocal/arrangement.json --vocal my_vocal.wav -o out/my_vocal_edit
```

## JSON schema (v1)
`grid{bpm,beats_per_bar,confidence,source,first_downbeat_s,beat_times}` · `key{name,candidates}` · `phrases[]` · `melody[]` (detected notes) ·
`bar_levels[]` (0–3 intensity) · `chords[]{start,end,bar,beat_in_bar,chord,function,confidence,melody_coverage,voicing,alternatives[]{chord,kind,delta,reason}}` ·
`strums[]{id,time,bar,beat_in_bar,gesture,dir,chord,velocity,spread_ms}` with gestures `hold, sparse, strum, single, muted_strum, pickup, stop, ending`.

## How it works
YIN pitch → notes/phrases → beat/downbeat from onset comb (or your markers) → key (Krumhansl) → **Viterbi chord decode over half-bar slots**
(melody fit on strong/long notes, functional transitions, change cost, guitar-voicing difficulty; top-3 keys decoded jointly) → colour/alternatives →
per-bar intensity from vocal energy/density + phrase shape → gesture patterns with chord-change attacks, breath stops, pickups, ending →
Karplus-Strong render. Rationale: `docs/decisions/0001-numpy-first-mvp.md`.

## What needs to be done (short version)
1. **You:** put a few dry solo-vocal recordings in `samples/owner/` (see `samples/owner/README.md`), run `arrange`, and report using `docs/EVALUATION.md`. This is the main blocker — the pipeline has only been validated on synthetic voices.
2. **Next engineering:** fix real-voice failures found above, add a licensed real-voice eval dataset, phrase-repetition-aware harmony, rubato/tempo changes, better guitar sound. Full list: `PROJECT_STATUS.md`.
3. **How the project got here / what we tried:** `docs/PROJECT_HISTORY.md` (running log; updated with every meaningful commit).

## Status, limits, evaluation
See `PROJECT_STATUS.md` (read the limitations!), `docs/EVALUATION.md` (how to test & report), `eval/run_eval.py`, `docs/DATA_SOURCES.md`.
