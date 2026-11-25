# Data sources, licences, acquisition

## Used so far
| Data | What | Licence / terms | Use |
|---|---|---|---|
| `vocal2chord/synth.py` tunes (Twinkle Twinkle, Amazing Grace, Ode to Joy) | Melodies as symbolic note lists (approximate, written from memory) | Underlying tunes are public domain; the note lists are ours | Ground-truth for unit tests, eval, and demo. **Rendered by a synthetic voice — not a real singer.** |

## Not yet used (could not be downloaded from this sandbox)
The agent sandbox's network proxy blocked Zenodo (HTTP 000), so no real-voice dataset was fetched or validated.
The table lists candidates **from memory — licences are unverified; check each landing page before any use,
especially commercial use**. Nothing here has been downloaded.

| Candidate | Useful for | Notes to verify |
|---|---|---|
| vocadito (Zenodo) | solo-vocal f0 + note annotations | licence; commercial use |
| MIR-1K | singing voice, pitch labels | research-only? |
| MedleyDB (vocal stems/melody annotations) | melody f0 | access request + licence terms |
| Choral Singing Dataset / Saraga / DALI | note/phrase labels | licence; audio availability |
| iKala | vocal f0 | availability/terms |

Acquisition recipe once network is available (per dataset): download from the official page, record URL + licence here,
place under `data/<name>/` (git-ignored), and add an adapter in `eval/` that yields `(audio, [(midi, onset, dur)])`
so `eval/run_eval.py` can score melody extraction on it.

## Owner-provided audio
Goes in `samples/owner/` (git-ignored). Processed locally only; no external services are called anywhere in this repo.
