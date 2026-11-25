# PROJECT STATUS

_Last updated: 2026-11-25 · Milestones M0–M4 implemented as an end-to-end MVP; **validated only on synthetic vocals.**_

## What works (measured — `python eval/run_eval.py`, 54 synthetic songs; EXP-001)
| Area | Result | Caveat |
|---|---|---|
| Melody (pitch-class note F1, ±50 ms) | 0.97 (exact-octave 0.88) | clean synthetic voice only |
| Key / tempo / downbeat | 100% / 100% / 100% | 3 tunes; downbeat prior tuned on them |
| Chord-tone rate on strong/long notes | **0.94** vs 0.65 tonic-only vs 0.55 I–V–vi–IV | measures fit, not taste |
| First/last chord tonic; changes marked by a stroke | 100% / 100% | |
| Arrangement | 5 gesture types, 3 intensity levels per song, breath stops, pickups, ending | no human listening yet |
| Speed | ~0.25 s analysis + ~2 s render per 30 s song | |
| Tests | 23 pass (`python -m pytest -q`) | |

Deliverables: CLI (`arrange`, `render`, `demo`), editable JSON (schema v1), MIDI, vocal+guitar mix, examples in `examples/`, docs in `docs/`.

## Honest limitations
1. **No real singer has been tested.** Sandbox network blocked public datasets (docs/DATA_SOURCES.md). Real voices (breath noise, scoops, vibrato, off-pitch, rubato) will degrade pitch/notes/beat estimates; expect to need `--bpm/--beats/--pickup-beats/--key` at first.
2. **Nobody has listened to the output** (the agent cannot listen). Voice-leading, strum feel, and guitar timbre (Karplus-Strong) are unvalidated by ears.
3. Downbeat from a solo voice is inherently ambiguous (half-bar shifts plausible); fixed-tempo grid only (no rubato/tempo changes).
4. Octave errors in melody are possible (harmony uses pitch class only, so impact is small).
5. Harmony: diatonic + a few borrowed chords, triads with colour/7th variants; no secondary dominants, modulations, or chord changes faster than half-bar slots; major/minor keys only (no modes). Voice-leading is only a shared-tone bonus.
6. Strumming: fixed pattern bank (4/4 and 3/4 rich; other meters basic); intensity from vocal energy/density plus phrase/arc heuristics, not learned.
7. Section contrast (verse/chorus) is only a gentle energy arc; repetition between phrases isn't exploited.

## Blockers / owner input
- **A few real vocal recordings** (WAV/FLAC/MP3, 20 s–4 min, dry solo vocal, ideally with a rough beat/bar marker file or at least the known BPM/key) in `samples/owner/` — needed to validate pitch/beat on real voices, which public data could not provide here.
- Optional: your own ground-truth chords for 1–2 songs to calibrate the chord model.

## Next tasks (highest value first)
1. Run on owner recordings; collect feedback using docs/EVALUATION.md; fix top failures (likely melody/onset robustness).
2. Real-voice melody evaluation on a licensed public dataset (verify licence; add adapter in `eval/`).
3. Phrase-repetition-aware progression (reuse chords for repeated melodic phrases), voice-leading cost, secondary dominants.
4. Tempo-varying/rubato grid; user-facing beat-edit UI (simple web page with waveform + chord/strum timeline).
5. Better guitar timbre (sample-based/soundfont) and fingerpicking/arpeggio gestures.

## Reproduce
`pip install -r requirements.txt && python -m pytest -q && python -m vocal2chord demo -o demo_out && python eval/run_eval.py`
