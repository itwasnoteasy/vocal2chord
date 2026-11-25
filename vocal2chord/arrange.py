"""Rhythm-guitar arrangement: per-bar intensity from the vocal, then gesture selection.

Gestures: hold, single (bass note), sparse/regular strum (D/U), muted_strum, pickup, stop (cut/pause), ending.
Everything is placed on an eighth-note grid derived from the beat/bar grid.
"""
from __future__ import annotations
import numpy as np
from .chords import best_voicing

# tokens: D down-strum, U up-strum, d bass single, x muted strum, . ring/rest
BANK_4 = {
    0: ["D......."],
    1: ["D...D...", "D.....D.", "D..d..D."],
    2: ["D.D.D.D.", "D.DU.UD.", "D...D.DU"],
    3: ["D.DU.UDU", "D.DUxUDU", "DxDUDxDU"],
}
BANK_3 = {0: ["D....."], 1: ["D..D.."], 2: ["D.DUD."], 3: ["D.DUDU"]}
VEL = [58, 72, 86, 100]


def _bank(bpb):
    if bpb == 4:
        return BANK_4
    if bpb == 3:
        return BANK_3
    return {k: ["D." * bpb if k else "D" + "." * (2 * bpb - 1)] for k in range(4)}


def _percentile_norm(x, min_range):
    x = np.asarray(x, dtype=float)
    ok = np.isfinite(x)
    if ok.sum() < 2 or np.ptp(x[ok]) < min_range:
        return np.full(len(x), 0.5)
    out = np.full(len(x), 0.5)
    lo, hi = x[ok].min(), x[ok].max()
    out[ok] = (x[ok] - lo) / (hi - lo)
    return out


def bar_levels(grid, notes, track, n_bars, phrases=()):
    bpb = grid.beats_per_bar
    per = 60.0 / grid.bpm
    on = grid.time_to_beat(np.array([n.onset for n in notes]))
    off = grid.time_to_beat(np.array([n.offset for n in notes]))
    dens, energy, cover, maxdur, nons = [], [], [], [], []
    for b in range(n_bars):
        b0, b1 = b * bpb, (b + 1) * bpb
        k = [i for i in range(len(notes)) if on[i] < b1 and off[i] > b0]
        starts = [i for i in k if b0 <= on[i] < b1]
        nons.append(len(starts))
        dens.append(len(starts) / bpb)
        cover.append(sum(min(off[i], b1) - max(on[i], b0) for i in k) / bpb)
        maxdur.append(max([off[i] - on[i] for i in k], default=0.0))
        t0, t1 = grid.beat_to_time(b0), grid.beat_to_time(b1)
        sel = (track.times >= t0) & (track.times < t1) & ~np.isnan(track.midi)
        energy.append(20 * np.log10(np.mean(track.rms[sel]) + 1e-9) if sel.any() else np.nan)
    dn, en = _percentile_norm(dens, 0.25), _percentile_norm(energy, 3.0)
    arc = np.array([0.25 + 0.75 * min(1.0, b / max(1.0, 0.75 * (n_bars - 1))) for b in range(n_bars)])
    arc[max(0, n_bars - 2):] = 0.6
    f = 0.35 * dn + 0.3 * en + 0.35 * arc
    lvl = np.clip(np.floor(f * 4.4), 0, 3).astype(float)
    lvl = np.clip(np.round(np.convolve(np.pad(lvl, 1, mode="edge"), [.25, .5, .25], mode="valid")), 0, 3)
    for ps, pe in phrases:                              # phrase shape: start restrained, build toward the breath
        b_s = int(grid.time_to_beat(notes[ps].onset) // bpb)
        b_e = int(grid.time_to_beat(notes[pe - 1].offset - 1e-3) // bpb)
        if b_e > b_s and b_s < n_bars:
            lvl[b_s] -= 1
            lvl[min(b_e, n_bars - 1)] += 1
    lvl = np.clip(lvl, 0, 3)
    for b in range(n_bars):
        if nons[b] <= 1:
            lvl[b] = min(lvl[b], 1)
        if maxdur[b] >= 0.75 * bpb and nons[b] <= 2:     # sustained vocal: leave space
            lvl[b] = max(0, lvl[b] - 1)
    if n_bars:
        lvl[0] = min(lvl[0], 1)
    return lvl.astype(int), dict(density=dens, coverage=cover, energy=energy)


def plan(grid, notes, phrases, chord_events, track, key):
    bpb = grid.beats_per_bar
    npos = 2 * bpb
    last_onset_beat = grid.time_to_beat(notes[-1].onset)
    n_bars = int((last_onset_beat + 0.2) // bpb) + 1
    levels, feats = bar_levels(grid, notes, track, n_bars, phrases)
    bank = _bank(bpb)

    def chord_at(beat):
        for e in chord_events:
            if e.start_beat <= beat + 1e-6 < e.end_beat:
                return e.chord
        return chord_events[-1].chord

    ph_end = [grid.time_to_beat(notes[e - 1].offset) for _, e in phrases]
    ph_start = [grid.time_to_beat(notes[s].onset) for s, _ in phrases]
    events = []
    prev_gap = False

    def add(beat, gesture, chord, direction="down", vel=80, **kw):
        events.append(dict(beat=float(beat), gesture=gesture, chord=chord.name if chord else None,
                           dir=direction, velocity=int(vel), **kw))

    for b in range(n_bars):
        b0 = b * bpb
        lvl = int(levels[b])
        final_bar = b == n_bars - 1
        end_pos = 0
        if final_bar:                                                 # ending lands where the closing chord begins
            end_pos = int(np.clip(round((chord_events[-1].start_beat - b0) * 2), 0, npos - 1))
        variants = bank[lvl]
        pat = list(variants[b % len(variants)])
        gap_bar = feats["coverage"][b] < 0.05 and b > 0
        if gap_bar:                                  # vocal rests all bar: cut the ring first, then a soft pulse
            pat = ["S"] + ["."] * (npos - 1) if not prev_gap else list(bank[0][0])
            lvl = 0
        prev_gap = gap_bar
        # chord change inside the bar must be marked by a stroke
        for p in range(1, npos):
            if chord_at(b0 + p / 2) != chord_at(b0 + (p - 1) / 2 - 1e-6) and pat[p] == ".":
                pat[p] = "D" if lvl > 0 else "d"
        # phrase ends followed by a real gap: cut the ring (breath/pause), silence the rest of the gap
        for pe, nxt in zip(ph_end[:-1], ph_start[1:]):
            if b0 <= pe < b0 + bpb and nxt - pe >= 1.0:
                p = int(np.ceil((pe - b0) * 2 - 1e-6))
                for q in range(p, npos):
                    if (b0 + q / 2) < nxt - 0.5:
                        pat[q] = "."
                if p < npos:
                    pat[p] = "S"
                # p == npos: breath starts on the barline; the next (gap) bar issues the cut
        # transition pickup: a quiet bass note of the next chord on the last eighth
        nb = b0 + bpb
        starts_phrase = (b + 1) in [int(s // bpb) for s in ph_start]
        if (pat[-1] == "." and chord_at(nb) != chord_at(nb - 0.5)
                and (starts_phrase or (lvl >= 2 and b % 2 == 1))):
            pat[-1] = "p"
        if final_bar:
            pat = [t if p < end_pos else "." for p, t in enumerate(pat)]
            pat[end_pos] = "E"
        for p, tok in enumerate(pat):
            beat = b0 + p / 2
            c = chord_at(beat)
            down = (p % 2 == 0)
            acc = 8 if p == 0 else (4 if down else -8)
            if tok == "D":
                g = "hold" if (lvl == 0 and p == 0) else ("sparse" if lvl == 1 else "strum")
                add(beat, g, c, "down", VEL[lvl] + acc, spread_ms=14)
            elif tok == "U":
                add(beat, "strum", c, "up", VEL[lvl] + acc, spread_ms=10)
            elif tok == "d":
                add(beat, "single", c, "down", VEL[lvl] + 2)
            elif tok == "x":
                add(beat, "muted_strum", c, "down", VEL[lvl])
            elif tok == "S":
                add(beat, "stop", None, "none", 0)
            elif tok == "E":
                add(beat, "ending", c, "down", 104, spread_ms=45, ring_beats=float(bpb))
            elif tok == "p":
                add(beat, "pickup", chord_at(nb), "down", VEL[max(0, lvl - 1)])
    for e in events:
        e["time"] = float(grid.beat_to_time(e["beat"]))
    events = [e for e in events if e["time"] >= -1e-3]   # bar 0 may start before the recording; drop pre-roll
    for i, e in enumerate(events):
        e["time"] = round(float(grid.beat_to_time(e["beat"])), 4)
        e["bar"] = int(e["beat"] // bpb) + 1
        e["beat_in_bar"] = round(e["beat"] % bpb + 1, 2)
        e["id"] = i
    return events, levels
