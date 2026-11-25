"""Guitar synthesis (Karplus-Strong plucks, vectorised per period) and MIDI export.

Rendering reads ONLY the exported arrangement dict, so edits to the JSON are what you hear.
"""
from __future__ import annotations
import numpy as np
from .chords import parse_chord, best_voicing, STRING_MIDI

SR = 44100
MAX_RING = 4.0


def _chord_at(chords, t):
    for c in chords:
        if c["start"] <= t + 1e-6 < c["end"]:
            return c["chord"]
    return chords[-1]["chord"] if t >= chords[-1]["end"] else chords[0]["chord"]


def resolve_notes(arr):
    """Expand strum events into per-string note dicts with cut times. Chord names come from the chord timeline."""
    chords = arr["chords"]
    evs = sorted(arr["strums"], key=lambda e: (e["time"], e.get("id", 0)))
    notes, last = [], {}
    for e in evs:
        t = e["time"]
        g = e["gesture"]
        if g in ("stop", "muted_strum"):
            for n in last.values():
                if n["cut"] is None:
                    n["cut"] = t
            last.clear()
            if g == "stop":
                continue
        name = e.get("chord_override") or _chord_at(chords, t)
        v = best_voicing(parse_chord(name))
        strings = v.strings
        if g == "muted_strum":
            for i, s in enumerate(strings):
                notes.append(dict(start=t, string=s, midi=STRING_MIDI[s] + v.frets[s], vel=e["velocity"],
                                  cut=t + 0.07, muted=True))
            continue
        if g in ("single", "pickup"):
            pick = [strings[0]]
        elif e["dir"] == "up":
            pick = strings[-min(4, len(strings)):][::-1]
        else:
            pick = strings
        spread = e.get("spread_ms", 12) / 1000.0
        for i, s in enumerate(pick):
            n = dict(start=t + i * spread, string=s, midi=STRING_MIDI[s] + v.frets[s], vel=e["velocity"], cut=None)
            if s in last and last[s]["cut"] is None:
                last[s]["cut"] = t + i * spread
            last[s] = n
            notes.append(n)
    return notes


_wave_cache: dict = {}


def _pluck(midi, dur, sr):
    key = (midi, round(dur * 20))
    if key in _wave_cache:
        return _wave_cache[key]
    f = 440.0 * 2 ** ((midi - 69) / 12)
    P = sr / f
    N = int(P - 0.5)
    frac = P - 0.5 - N
    rng = np.random.default_rng(midi)
    ex = rng.uniform(-1, 1, N + 2)
    ex = np.convolve(ex, [0.5, 0.5], mode="same")                      # soften the pick
    pk = max(1, int(0.18 * N))
    ex[pk:] -= 0.6 * ex[:-pk] if pk < len(ex) else 0                    # pick-position comb
    g = 10 ** (-3.0 / (f * 2.4))                                         # ~2.4 s T60 before averaging loss
    h = np.array([(1 - frac) / 2, 0.5, frac / 2]) * g
    n_out = int(dur * sr)
    off = N + 2                                   # left padding so delayed taps never index negative
    yb = np.zeros(off + n_out + N + 2)
    m = min(len(ex), n_out)
    yb[off:off + m] = ex[:m]
    for s in range(N, n_out, N):                  # one period per numpy op: y[n] += g*avg(y[n-N], y[n-N-1], y[n-N-2])
        L = min(N, n_out - s)
        i = off + s
        yb[i:i + L] += h[0] * yb[i - N:i - N + L] + h[1] * yb[i - N - 1:i - N - 1 + L] + h[2] * yb[i - N - 2:i - N - 2 + L]
    y = yb[off:off + n_out]
    y /= max(1e-9, np.abs(y).max())
    _wave_cache[key] = y
    return y


def render_guitar(arr, sr=SR, tail=3.0):
    notes = resolve_notes(arr)
    end = max((min(n["cut"] if n["cut"] else n["start"] + MAX_RING, n["start"] + MAX_RING) for n in notes), default=1.0)
    out = np.zeros(int((end + tail) * sr))
    for n in notes:
        dur = min((n["cut"] - n["start"]) if n["cut"] is not None else MAX_RING, MAX_RING) + 0.012
        if dur <= 0.012:
            continue
        w = _pluck(n["midi"], dur, sr).copy()
        if n.get("muted"):
            w *= np.exp(-np.arange(len(w)) / sr / 0.02) * 0.5
        fade = min(len(w), int(0.012 * sr))
        w[-fade:] *= np.linspace(1, 0, fade)
        a = max(0, int(n["start"] * sr))
        if a >= len(out):
            continue
        out[a:a + len(w)] += w[:max(0, len(out) - a)] * (n["vel"] / 127.0) ** 1.3 * 0.25
    return out.astype(np.float32), sr


def mix(vocal, vsr, guitar, gsr, guitar_db=-4.0):
    from .audio import resample
    v = resample(vocal, vsr, gsr)
    n = max(len(v), len(guitar))
    v = np.pad(v, (0, n - len(v)))
    g = np.pad(guitar, (0, n - len(guitar)))
    rv = np.sqrt(np.mean(v[np.abs(v) > 0.01] ** 2) + 1e-12) if np.any(np.abs(v) > 0.01) else 0.1
    rg = np.sqrt(np.mean(g[np.abs(g) > 0.005] ** 2) + 1e-12) if np.any(np.abs(g) > 0.005) else 0.1
    g = g * (rv / rg) * 10 ** (guitar_db / 20)
    m = v + g
    return (m / max(1.0, np.abs(m).max() / 0.95)).astype(np.float32), g.astype(np.float32)


def write_midi(arr, path, include_melody=True):
    import mido
    tpq, bpm = 480, arr["grid"]["bpm"]
    spt = lambda s: int(round(s * bpm / 60.0 * tpq))
    mid = mido.MidiFile(ticks_per_beat=tpq)
    meta = mido.MidiTrack()
    meta.append(mido.MetaMessage("set_tempo", tempo=mido.bpm2tempo(bpm), time=0))
    bpb = arr["grid"]["beats_per_bar"]
    meta.append(mido.MetaMessage("time_signature", numerator=bpb, denominator=4, time=0))
    mid.tracks.append(meta)

    def track(notes, channel, program, name):
        tr = mido.MidiTrack()
        tr.append(mido.MetaMessage("track_name", name=name, time=0))
        tr.append(mido.Message("program_change", channel=channel, program=program, time=0))
        ev = []
        for midi, on, off, vel in notes:
            ev.append((spt(on), 1, mido.Message("note_on", channel=channel, note=int(midi), velocity=int(vel))))
            ev.append((max(spt(off), spt(on) + 1), 0, mido.Message("note_off", channel=channel, note=int(midi), velocity=0)))
        last = 0
        for t, _, m in sorted(ev, key=lambda x: (x[0], x[1])):
            m.time = t - last
            last = t
            tr.append(m)
        mid.tracks.append(tr)

    gn = [(n["midi"], n["start"], n["cut"] if n["cut"] is not None else n["start"] + 2.0, max(1, min(127, n["vel"])))
          for n in resolve_notes(arr) if not n.get("muted")]
    track(gn, 0, 25, "Guitar")
    if include_melody:
        track([(n["midi"], n["onset"], n["offset"], 80) for n in arr["melody"]], 1, 54, "Vocal melody (detected)")
    mid.save(path)
