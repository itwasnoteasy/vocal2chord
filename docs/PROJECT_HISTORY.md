# Project history (running log)

High-level story of vocal2chord: the problem, what we tried, what broke, what changed, and where we are.
**Append a dated entry whenever you commit meaningful work or start a new problem.** Keep entries short; link to
`docs/decisions/`, `docs/experiments/`, and `PROJECT_STATUS.md` for detail. Newest entries at the bottom; update "Current state" in place.

## The problem
Given a **solo vocal recording of any song** (any key, own timing), generate a convincing **rhythm-guitar accompaniment**:
a coherent chord progression with alternatives, and a dynamic strumming arrangement (strums, holds, mutes, pickups, stops, ending),
audible against the vocal and editable as JSON. Not song identification; harmonise the melody the singer actually sang.

## Current state (update in place)
- End-to-end MVP works: audio -> pitch -> notes/phrases -> grid -> key -> Viterbi chords + alternatives -> arrangement -> guitar render / MIDI / JSON.
- Validated **only on synthetic vocals** (3 public-domain tunes); no real singer tested, nobody has listened to outputs yet.
- Biggest open items: real-voice validation (needs owner recordings), listening feedback, rubato/tempo changes, phrase-repetition-aware harmony.
- Authoritative to-do list: `PROJECT_STATUS.md`.

## Timeline

### 2026-11-25 — Project start, first end-to-end MVP
- **Problem:** blank repo; build an audible, testable baseline fast rather than survey literature.
- **Approach:** lightweight numpy/scipy pipeline (own YIN pitch tracker, onset-comb beat grid, Krumhansl key, Viterbi chord decode, pattern-bank strumming, Karplus-Strong guitar). Rationale and rejected options: `docs/decisions/0001-numpy-first-mvp.md`.
- **Problems hit and fixes:**
  - YIN octave errors on vowels with strong 2nd harmonic -> local-median octave folding + merge of octave-fragment notes; harmony uses pitch class only so impact is limited.
  - Downbeat from a solo voice is ambiguous (half-bar shifts) -> metrical-accent scoring + first-note-is-downbeat prior; manual `--bpm/--beats/--pickup-beats` overrides.
  - Eval metric bug (scoring notes at onset penalised jitter at chord boundaries) -> score at note midpoint.
  - Closing bar missed when final note onset fell just before a barline -> onset tolerance; ending gesture now lands on the final chord.
  - Phrase-gap threshold too strict at fast tempos -> lowered to 0.22 s.
- **Result:** EXP-001 (`docs/experiments/EXP-001-baseline.md`): chord-tone rate 0.94 vs 0.65 tonic-only vs 0.55 I-V-vi-IV; note F1 0.97 (pitch class). Caveat: synthetic data, optimistic.
- **Blocked:** public real-voice datasets (sandbox proxy blocked Zenodo). Candidates listed unverified in `docs/DATA_SOURCES.md`.
- **Next:** owner supplies real vocals -> measure/fix real-voice failures.
