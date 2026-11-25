# 0001 — Lightweight numpy/scipy pipeline, own YIN and Karplus-Strong

**Context.** Blank repo; goal is an end-to-end audible MVP that runs locally with no GPU and no downloads.
**Decision.** Implement pitch tracking (YIN), note segmentation, beat/downbeat estimation, key + Viterbi chord
selection, gesture planning, and a Karplus-Strong guitar renderer directly on numpy/scipy. Dependencies: numpy, scipy,
soundfile, mido (all permissive-licensed, maintained).

| Option | Why not (for the MVP) |
|---|---|
| CREPE / pYIN / basic-pitch / librosa | Heavier installs (TensorFlow/torch/numba) and, for neural models, weights/licences to check. Revisit if real-voice melody accuracy proves insufficient — the `PitchTrack` interface is the swap point. |
| madmom / beat_this beat trackers | Trained on accompanied music; a solo voice has few percussive cues. Onset-comb search on note onsets is adequate for steady singing; manual `--bpm/--beats/--pickup-beats` override exists. |
| FluidSynth + SoundFont | System package + a licensed .sf2 needed; Karplus-Strong needs neither and is deterministic. MIDI is also exported so any DAW/synth can be used. |
| Learned harmonisation model | No licensed/accessible training data in this sandbox; interpretable Viterbi gives alternatives + reasons, which the brief asks for. |

**Consequences.** Real-voice robustness (breathy/noisy/vibrato-heavy singing) is unmeasured — see PROJECT_STATUS.md.
