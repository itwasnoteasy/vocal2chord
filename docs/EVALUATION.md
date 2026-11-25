# How to evaluate and report feedback

1. Run on your vocal: `python -m vocal2chord arrange samples/owner/<file>.wav -o out/<name>` (add `--beats file` if you have markers).
2. Open `out/<name>/chord_chart.txt` (chords, alternatives, grid confidence) and listen to `mix.wav` (vocal + guitar). `guitar.wav` is guitar only; `arrangement.mid` opens in any DAW.
3. Try alternatives: edit `chords[i].chord` in `arrangement.json` (e.g. swap in an `alternatives[].chord`) and re-render:
   `python -m vocal2chord render out/<name>/arrangement.json --vocal samples/owner/<file>.wav -o out/<name>_edit`
   Strum events follow the chord timeline automatically. Edit `strums[]` (`gesture`, `time`, `dir`, `velocity`) to change rhythm.
4. Rate each (1–5) and note timestamps for problems:
   - **Melody**: were the detected notes (`melody` in JSON) right? Wrong octave? Missed/extra notes?
   - **Grid**: tempo and bar-1 correct? (Else pass `--bpm`, `--beats`, `--pickup-beats`.)
   - **Chords**: fit, progression flow, ending; was a better chord in the alternatives?
   - **Strumming**: does it follow phrasing/energy; breaths; chord-change attacks; ending.
5. Report: the audio (or description if private), `arrangement.json`, the ratings and timestamps. Objective regression numbers: `python eval/run_eval.py`.

Known measurement gaps: no real-voice ground truth yet; no human listening panel; chord-tone rate rewards safe choices.
