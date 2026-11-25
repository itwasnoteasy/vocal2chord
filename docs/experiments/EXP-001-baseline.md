# EXP-001 — M1/M2 baseline on synthetic ground-truth vocals

- **Hypothesis:** melody-informed Viterbi harmonisation yields chords that fit sung strong/long notes far better than melody-blind baselines, with correct key/tempo/downbeat from a solo vocal.
- **Data:** 3 public-domain tunes × 6 transpositions × 3 tempos (54 songs), synthetic voice (vibrato, ±25 cent detune, 12 ms timing jitter). See docs/DATA_SOURCES.md.
- **Baselines (same estimated grid):** tonic-only; I–V–vi–IV one chord per bar.
- **Command:** `python eval/run_eval.py --out docs/experiments/EXP-001-baseline.md`
- **Caveats (read these):** synthetic voices are far cleaner than real ones; only 3 tunes, and the downbeat prior was adjusted while looking at them, so downbeat/key numbers are optimistic. "Chord-tone rate" measures fit, not musical taste — a tonic-heavy or all-colour progression can score well and sound dull. Not a substitute for listening (docs/EVALUATION.md).
- **Findings during development (honest log):**
  - Octave errors in YIN on a vowel with strong 2nd harmonic folded whole notes up an octave (exact-MIDI F1 0.88 vs pitch-class 0.97). Harmony only uses pitch class, so impact is limited; short octave-fragments are merged.
  - Downbeat from a solo vocal is ambiguous (e.g. Twinkle's half note on beat 3 vs beat 1: a 2-beat shift is plausible and changes nothing harmonically). Added first-note prior + manual `--pickup-beats`/`--beats`.
  - Early metric bug (scoring a note at its onset penalised ±jitter at chord boundaries) fixed by scoring at note midpoints.
- **Decision:** keep the pipeline; next step is real-voice validation (owner samples) — see PROJECT_STATUS.md.

## Results
54 synthetic cases (tunes x transpositions x tempos, timing jitter 12 ms, detune ±25 cents)

| metric | value |
|---|---|
| note F1 (pitch-class, onset ±50 ms) | 0.973 |
| note F1 (exact MIDI incl. octave) | 0.883 |
| key correct | 100.0% |
| tempo within 3% | 100.0% |
| downbeat phase exact | 100.0% |
| downbeat within a half-bar shift | 100.0% |
| strong-note chord-tone rate: vocal2chord | 0.937 |
|   baseline: tonic only | 0.650 |
|   baseline: I-V-vi-IV loop | 0.549 |
| chords per bar | 1.10 |
| first chord is tonic | 100.0% |
| last chord is tonic | 100.0% |
| mean voicing difficulty (0 open .. 2+ barre) | 0.94 |
| distinct gestures used | 5.0 |
| distinct intensity levels | 3.1 |
| chord changes marked by a stroke | 100.0% |
| analysis seconds / song | 0.24 |

<details><summary>per-case</summary>

| case | F1 | key | tempo | dnbt | compat | tonic-only | loop | chords |
|---|---|---|---|---|---|---|---|---|
| twinkle/+0/80bpm | 1.00 | Y | Y | Y | 1.00 | 0.57 | 0.45 | 21 |
| twinkle/+0/100bpm | 1.00 | Y | Y | Y | 1.00 | 0.57 | 0.45 | 21 |
| twinkle/+0/120bpm | 1.00 | Y | Y | Y | 1.00 | 0.57 | 0.45 | 21 |
| twinkle/+2/80bpm | 0.92 | Y | Y | Y | 1.00 | 0.57 | 0.45 | 21 |
| twinkle/+2/100bpm | 0.87 | Y | Y | Y | 1.00 | 0.57 | 0.45 | 21 |
| twinkle/+2/120bpm | 0.86 | Y | Y | Y | 1.00 | 0.57 | 0.45 | 21 |
| twinkle/+5/80bpm | 1.00 | Y | Y | Y | 1.00 | 0.57 | 0.45 | 21 |
| twinkle/+5/100bpm | 1.00 | Y | Y | Y | 1.00 | 0.57 | 0.45 | 21 |
| twinkle/+5/120bpm | 1.00 | Y | Y | Y | 1.00 | 0.57 | 0.45 | 21 |
| twinkle/+7/80bpm | 0.86 | Y | Y | Y | 1.00 | 0.57 | 0.45 | 21 |
| twinkle/+7/100bpm | 0.93 | Y | Y | Y | 1.00 | 0.57 | 0.45 | 21 |
| twinkle/+7/120bpm | 1.00 | Y | Y | Y | 1.00 | 0.57 | 0.45 | 21 |
| twinkle/+9/80bpm | 1.00 | Y | Y | Y | 1.00 | 0.57 | 0.45 | 21 |
| twinkle/+9/100bpm | 0.90 | Y | Y | Y | 1.00 | 0.57 | 0.45 | 21 |
| twinkle/+9/120bpm | 0.81 | Y | Y | Y | 1.00 | 0.57 | 0.45 | 21 |
| twinkle/+11/80bpm | 1.00 | Y | Y | Y | 1.00 | 0.57 | 0.45 | 21 |
| twinkle/+11/100bpm | 1.00 | Y | Y | Y | 1.00 | 0.57 | 0.45 | 21 |
| twinkle/+11/120bpm | 0.90 | Y | Y | Y | 1.00 | 0.57 | 0.45 | 21 |
| amazing_grace/+0/80bpm | 0.98 | Y | Y | Y | 0.96 | 0.74 | 0.59 | 7 |
| amazing_grace/+0/100bpm | 1.00 | Y | Y | Y | 0.96 | 0.74 | 0.59 | 7 |
| amazing_grace/+0/120bpm | 0.98 | Y | Y | Y | 0.96 | 0.74 | 0.59 | 7 |
| amazing_grace/+2/80bpm | 0.91 | Y | Y | Y | 0.96 | 0.74 | 0.59 | 7 |
| amazing_grace/+2/100bpm | 0.97 | Y | Y | Y | 0.96 | 0.74 | 0.59 | 7 |
| amazing_grace/+2/120bpm | 1.00 | Y | Y | Y | 0.96 | 0.73 | 0.58 | 7 |
| amazing_grace/+5/80bpm | 1.00 | Y | Y | Y | 0.96 | 0.74 | 0.59 | 7 |
| amazing_grace/+5/100bpm | 1.00 | Y | Y | Y | 0.96 | 0.73 | 0.58 | 7 |
| amazing_grace/+5/120bpm | 1.00 | Y | Y | Y | 0.96 | 0.74 | 0.59 | 7 |
| amazing_grace/+7/80bpm | 1.00 | Y | Y | Y | 0.92 | 0.73 | 0.58 | 9 |
| amazing_grace/+7/100bpm | 0.95 | Y | Y | Y | 0.96 | 0.73 | 0.58 | 7 |
| amazing_grace/+7/120bpm | 1.00 | Y | Y | Y | 0.96 | 0.73 | 0.58 | 7 |
| amazing_grace/+9/80bpm | 1.00 | Y | Y | Y | 0.96 | 0.74 | 0.59 | 7 |
| amazing_grace/+9/100bpm | 0.98 | Y | Y | Y | 0.96 | 0.74 | 0.59 | 7 |
| amazing_grace/+9/120bpm | 1.00 | Y | Y | Y | 0.96 | 0.74 | 0.59 | 7 |
| amazing_grace/+11/80bpm | 1.00 | Y | Y | Y | 0.92 | 0.73 | 0.58 | 9 |
| amazing_grace/+11/100bpm | 1.00 | Y | Y | Y | 0.96 | 0.74 | 0.59 | 7 |
| amazing_grace/+11/120bpm | 1.00 | Y | Y | Y | 0.96 | 0.73 | 0.58 | 7 |
| ode_to_joy/+0/80bpm | 0.95 | Y | Y | Y | 0.86 | 0.64 | 0.61 | 11 |
| ode_to_joy/+0/100bpm | 1.00 | Y | Y | Y | 0.86 | 0.64 | 0.61 | 7 |
| ode_to_joy/+0/120bpm | 1.00 | Y | Y | Y | 0.82 | 0.64 | 0.61 | 9 |
| ode_to_joy/+2/80bpm | 1.00 | Y | Y | Y | 0.93 | 0.64 | 0.61 | 9 |
| ode_to_joy/+2/100bpm | 1.00 | Y | Y | Y | 0.89 | 0.64 | 0.61 | 7 |
| ode_to_joy/+2/120bpm | 0.91 | Y | Y | Y | 0.89 | 0.64 | 0.61 | 7 |
| ode_to_joy/+5/80bpm | 0.97 | Y | Y | Y | 0.82 | 0.64 | 0.61 | 7 |
| ode_to_joy/+5/100bpm | 1.00 | Y | Y | Y | 0.86 | 0.64 | 0.61 | 11 |
| ode_to_joy/+5/120bpm | 1.00 | Y | Y | Y | 0.86 | 0.64 | 0.61 | 11 |
| ode_to_joy/+7/80bpm | 1.00 | Y | Y | Y | 0.82 | 0.64 | 0.61 | 9 |
| ode_to_joy/+7/100bpm | 0.95 | Y | Y | Y | 0.82 | 0.64 | 0.61 | 7 |
| ode_to_joy/+7/120bpm | 1.00 | Y | Y | Y | 0.79 | 0.64 | 0.61 | 7 |
| ode_to_joy/+9/80bpm | 1.00 | Y | Y | Y | 0.89 | 0.64 | 0.61 | 11 |
| ode_to_joy/+9/100bpm | 1.00 | Y | Y | Y | 0.82 | 0.64 | 0.61 | 9 |
| ode_to_joy/+9/120bpm | 0.97 | Y | Y | Y | 0.89 | 0.64 | 0.61 | 9 |
| ode_to_joy/+11/80bpm | 0.97 | Y | Y | Y | 0.79 | 0.64 | 0.61 | 7 |
| ode_to_joy/+11/100bpm | 1.00 | Y | Y | Y | 0.89 | 0.64 | 0.61 | 11 |
| ode_to_joy/+11/120bpm | 1.00 | Y | Y | Y | 0.86 | 0.64 | 0.61 | 11 |

</details>
