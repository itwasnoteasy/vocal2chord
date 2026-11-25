import json, os, sys
import numpy as np
import pytest
sys.path.insert(0, os.path.join(os.path.dirname(__file__), ".."))
from vocal2chord.chords import Chord, QUALITIES, MINORISH, best_voicing, parse_chord, STRING_MIDI
from vocal2chord.pitch import track_pitch
from vocal2chord.notes import segment_notes, find_phrases
from vocal2chord.grid import estimate_grid
from vocal2chord.synth import TUNES, score_to_notes, sing
from vocal2chord.pipeline import analyze_array
from vocal2chord.render import render_guitar, resolve_notes, write_midi, mix


def _arr(name="twinkle", transpose=0, bpm=100, **kw):
    t = TUNES[name]
    gt = score_to_notes(t, bpm=bpm, transpose=transpose, jitter=0.01)
    y, sr = sing(gt)
    return analyze_array(y, sr, beats_per_bar=t["bpb"], **kw), (y, sr), gt


def _arr_known_grid(name="twinkle", **kw):
    """Same but with true beat markers, so arrangement tests do not depend on downbeat estimation."""
    t = TUNES[name]
    pick = {"twinkle": 0, "amazing_grace": 1, "ode_to_joy": 0}[name]
    per = 0.6
    beats = [0.5 + (pick + i) * per for i in range(120)]
    gt = score_to_notes(t, bpm=100, jitter=0.01)
    y, sr = sing(gt)
    return analyze_array(y, sr, beats=beats, beats_per_bar=t["bpb"], **kw), (y, sr), gt


# ---- chords -------------------------------------------------------------------------------
def test_parse_roundtrip():
    for r in range(12):
        for q in QUALITIES:
            c = Chord(r, q)
            assert parse_chord(c.name) == c, c.name


def test_voicings_are_correct_and_playable():
    for r in range(12):
        for q in QUALITIES:
            c = Chord(r, q)
            v = best_voicing(c)
            pcs = {m % 12 for m in v.midi}
            triad = Chord(r, "min" if q in MINORISH else "maj").pcs
            assert pcs <= c.pcs or pcs <= triad, (c.name, v.frets)
            assert len(v.strings) >= 4
            assert max(f for f in v.frets if f is not None) <= 15


# ---- pitch / notes ---------------------------------------------------------------------------
@pytest.mark.parametrize("midi", [48, 55, 60, 67, 72, 79])
def test_yin_pure_harmonic_tone(midi):
    sr = 16000
    t = np.arange(int(0.6 * sr)) / sr
    f = 440 * 2 ** ((midi - 69) / 12)
    y = sum(np.sin(2 * np.pi * f * h * t) / h for h in range(1, 6)).astype(np.float32)
    tr = track_pitch(y, sr)
    m = tr.midi[~np.isnan(tr.midi)]
    assert len(m) > 30
    assert abs(np.median(m) - midi) < 0.2


def test_silence_is_unvoiced():
    tr = track_pitch(np.zeros(16000, dtype=np.float32), 16000)
    assert np.all(np.isnan(tr.midi))


def test_notes_recovered_pitch_class_and_onsets():
    gt = score_to_notes(TUNES["twinkle"], bpm=100, jitter=0.01)
    y, sr = sing(gt)
    notes = segment_notes(track_pitch(y, sr))
    assert [n.midi % 12 for n in notes] == [m % 12 for m, _, _ in gt]
    assert max(abs(n.onset - g[1]) for n, g in zip(notes, gt)) < 0.06
    assert len(find_phrases(notes)) == 6


# ---- grid ---------------------------------------------------------------------------------
def test_supplied_markers_are_used():
    gt = score_to_notes(TUNES["twinkle"], bpm=100)
    y, sr = sing(gt)
    notes = segment_notes(track_pitch(y, sr))
    beats = [0.5 + i * 0.6 for i in range(40)]
    g = estimate_grid(notes, find_phrases(notes), len(y) / sr, beats=beats)
    assert g.source == "markers" and abs(g.bpm - 100) < 0.01 and abs(g.beats[0] - 0.5) < 1e-6


def test_estimated_tempo_close():
    arr, _, _ = _arr(bpm=90)
    assert abs(arr["grid"]["bpm"] - 90) < 3


# ---- harmony ------------------------------------------------------------------------------
@pytest.mark.parametrize("name", list(TUNES))
def test_key_and_cadence(name):
    arr, _, _ = _arr(name)
    tonic = TUNES[name]["tonic"] % 12
    assert arr["key"]["tonic"] == tonic and arr["key"]["mode"] == "major"
    assert parse_chord(arr["chords"][-1]["chord"]).root == tonic
    assert all(len(c["alternatives"]) >= 1 for c in arr["chords"])


def test_transposition_invariance_of_function():
    a, _, _ = _arr("twinkle", 0)
    b, _, _ = _arr("twinkle", 5)
    assert [c["function"] for c in a["chords"]] == [c["function"] for c in b["chords"]]
    assert [c["bar"] for c in a["chords"]] == [c["bar"] for c in b["chords"]]


def test_melody_compat_beats_tonic_only():
    arr, _, gt = _arr("twinkle")
    from vocal2chord.render import _chord_at
    ok = sum(1 for m, on, d in gt if (m % 12) in parse_chord(_chord_at(arr["chords"], on + d / 2)).pcs)
    assert ok / len(gt) > 0.85


# ---- arrangement ------------------------------------------------------------------------------
def test_arrangement_is_dynamic_and_complete():
    arr, _, _ = _arr_known_grid("twinkle")
    gest = {e["gesture"] for e in arr["strums"]}
    assert "ending" in gest and len(gest) >= 3
    assert len(set(arr["bar_levels"])) >= 2
    assert sum(e["gesture"] == "ending" for e in arr["strums"]) == 1
    last = max(arr["strums"], key=lambda e: e["time"])
    assert last["gesture"] == "ending"
    times = [e["time"] for e in arr["strums"]]
    assert times == sorted(times) and times[0] >= 0
    for c in arr["chords"][1:]:   # every chord change is marked by an attack
        assert any(abs(e["time"] - c["start"]) < 0.06 and e["gesture"] != "stop" for e in arr["strums"])


def test_phrase_gap_creates_stop():
    # long breath between two phrases -> a 'stop' (cut) gesture
    t = dict(bpb=4, tonic=60, notes=[(0, 1), (4, 1), (7, 2), (None, 4), (0, 1), (4, 1), (7, 1), (0, 4)])
    y, sr = sing(score_to_notes(t, bpm=100))
    arr = analyze_array(y, sr, beats_per_bar=4)
    assert any(e["gesture"] == "stop" for e in arr["strums"])


def test_requires_vocal():
    with pytest.raises(ValueError):
        analyze_array(np.zeros(16000, dtype=np.float32), 16000)


# ---- render / edit ---------------------------------------------------------------------------
def _peak_hz(x, sr, lo, hi):
    spec = np.abs(np.fft.rfft(x * np.hanning(len(x)), 1 << 17))
    f = np.fft.rfftfreq(1 << 17, 1 / sr)
    sel = (f > lo) & (f < hi)
    return f[sel][np.argmax(spec[sel])]


def test_rendered_guitar_pitches_match_voicing():
    base = dict(chords=[dict(start=0, end=9, chord="Am")], grid=dict(bpm=100, beats_per_bar=4), melody=[])
    for gesture in ("single", "strum"):
        arr = dict(base, strums=[dict(id=0, time=0.1, gesture=gesture, dir="down", velocity=100, spread_ms=0)])
        g, sr = render_guitar(arr)
        x = g[int(0.15 * sr):int(1.2 * sr)]
        assert abs(_peak_hz(x, sr, 90, 140) - 110.0) < 1.5, gesture     # A2 string present, in tune
    # every open-string pitch is in tune (<8 cents) when plucked alone
    for m in STRING_MIDI:
        f = 440 * 2 ** ((m - 69) / 12)
        arr = dict(base, chords=[dict(start=0, end=9, chord="Em")],
                   strums=[dict(id=0, time=0.05, gesture="single", dir="down", velocity=100)])
        w = __import__("vocal2chord.render", fromlist=["_pluck"])._pluck(m, 1.0, 44100)
        pk = _peak_hz(w[2000:30000], 44100, f * 0.9, f * 1.1)
        assert abs(1200 * np.log2(pk / f)) < 12, (m, pk, f)


def test_edit_chord_changes_audio_and_strum_follows_timeline():
    arr, (y, sr), _ = _arr_known_grid("twinkle")
    g1, _ = render_guitar(arr)
    arr2 = json.loads(json.dumps(arr))
    arr2["chords"][0]["chord"] = "Am"
    n1 = [n["midi"] for n in resolve_notes(arr) if n["start"] < 1.0]
    n2 = [n["midi"] for n in resolve_notes(arr2) if n["start"] < 1.0]
    assert n1 != n2
    g2, _ = render_guitar(arr2)
    assert not np.allclose(g1[:len(g2)][:44100], g2[:44100])


def test_json_roundtrip_and_midi(tmp_path):
    arr, (y, sr), _ = _arr("amazing_grace")
    p = tmp_path / "a.json"
    p.write_text(json.dumps(arr))
    arr2 = json.loads(p.read_text())
    for k in ("schema_version", "meta", "grid", "key", "phrases", "melody", "chords", "strums", "bar_levels"):
        assert k in arr2
    write_midi(arr2, str(tmp_path / "a.mid"))
    import mido
    mf = mido.MidiFile(str(tmp_path / "a.mid"))
    assert len(mf.tracks) == 3 and mf.length > 10
    g, gsr = render_guitar(arr2)
    m, _ = mix(y, sr, g, gsr)
    assert np.isfinite(m).all() and np.abs(m).max() <= 1.0
