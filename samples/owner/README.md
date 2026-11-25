# Owner sample slot

Drop your solo-vocal recordings here (git-ignored, never uploaded anywhere — everything runs locally).

Preferred: WAV/FLAC/MP3/M4A, mono or stereo, any sample rate, 20 s – 4 min, dry vocal (no backing track).
Optional: `<name>.beats.txt` — one beat time in seconds per line (or a JSON list); the **first line must be a downbeat**.

```
python -m vocal2chord arrange samples/owner/mysong.wav -o out/mysong
python -m vocal2chord arrange samples/owner/mysong.wav --beats samples/owner/mysong.beats.txt -o out/mysong
```
See docs/EVALUATION.md for what to report.
