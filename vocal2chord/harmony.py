"""Key estimation and phrase-level progression selection.

Chord choice is a Viterbi decode over bar-half slots (bar in 3/4): the emission scores melody fit
(chord tones on strong/long notes), the transition scores functional plausibility, change cost and
shared tones, and an emission term penalises hard-to-play chords. Top key candidates are all decoded and
the best total path wins, so key (and relative major/minor) is decided together with the progression.
"""
from __future__ import annotations
from dataclasses import dataclass
import numpy as np
from .chords import Chord, QUALITIES, MINORISH, best_voicing

MAJOR = [0, 2, 4, 5, 7, 9, 11]
MINOR = [0, 2, 3, 5, 7, 8, 10, 11]
KP_MAJ = np.array([6.35, 2.23, 3.48, 2.33, 4.38, 4.09, 2.52, 5.19, 2.39, 3.66, 2.29, 2.88])
KP_MIN = np.array([6.33, 2.68, 3.52, 5.38, 2.60, 3.53, 2.54, 4.75, 3.98, 2.69, 3.34, 3.17])
PC = ["C", "Db", "D", "Eb", "E", "F", "F#", "G", "Ab", "A", "Bb", "B"]


@dataclass
class KeyCand:
    tonic: int
    mode: str   # 'major' | 'minor'
    score: float

    @property
    def name(self):
        return PC[self.tonic] + ("" if self.mode == "major" else "m")

    @property
    def scale(self):
        return {(self.tonic + i) % 12 for i in (MAJOR if self.mode == "major" else MINOR)}


def estimate_key(notes, top=3) -> list[KeyCand]:
    if not notes:
        return [KeyCand(0, "major", 0.0)]
    h = np.zeros(12)
    for n in notes:
        h[n.midi % 12] += min(n.dur, 2.0)
    out = []
    for t in range(12):
        for mode, prof in (("major", KP_MAJ), ("minor", KP_MIN)):
            r = np.corrcoef(h, np.roll(prof, t))[0, 1] if h.std() > 0 else 0.0
            r += 0.10 * (notes[-1].midi % 12 == t) + 0.04 * (notes[0].midi % 12 == t)
            out.append(KeyCand(t, mode, float(r)))
    return sorted(out, key=lambda k: -k.score)[:top]


# ---- slots -----------------------------------------------------------------------------------
@dataclass
class Slot:
    b0: float                 # beat range [b0, b1)
    b1: float
    items: list               # (pc, weight, dur_beats)
    phrase_end: bool = False
    bar_start: bool = False
    last: bool = False


def make_slots(grid, notes, phrases, slot_beats) -> list[Slot]:
    if not notes:
        return []
    ob = grid.time_to_beat(np.array([n.onset for n in notes]))
    fb = grid.time_to_beat(np.array([n.offset for n in notes]))
    bpb = grid.beats_per_bar
    n_bars = int((ob[-1] + 0.2) // bpb) + 1            # the final bar runs to its end so a closing chord gets a full bar
    n_slots = int(n_bars * bpb // slot_beats)
    ends = {int(grid.time_to_beat(notes[e - 1].offset) // slot_beats) for _, e in phrases[:-1]}
    slots = []
    for s in range(n_slots):
        b0, b1 = s * slot_beats, (s + 1) * slot_beats
        items = []
        for n, o, f in zip(notes, ob, fb):
            ov = min(f, b1) - max(o, b0)
            if ov <= 0:
                continue
            strong = b0 <= o < b1 and abs(o - round(o)) < 0.2 and int(round(o)) % 2 == 0
            items.append((n.midi % 12, ov * (1.0 + 0.5 * strong) + (0.5 if strong else 0.0), ov))
        slots.append(Slot(b0, b1, items, s in ends, (b0 % bpb) == 0, b1 > ob[-1]))   # last: from the slot holding the final onset
    return slots


def note_compat(pc, chord: Chord, scale, dur_beats):
    rel = (pc - chord.root) % 12
    ivs = QUALITIES[chord.quality]
    if rel in ivs[:3]:
        return 1.0
    if rel in ivs:
        return 0.85
    if pc in scale:
        return -0.3 if dur_beats <= 0.5 else -0.8
    return -0.8


def fit(chord: Chord, slot: Slot, scale) -> float:
    tw = sum(w for _, w, _ in slot.items)
    if tw <= 0:
        return 0.0
    s = sum(w * note_compat(pc, chord, scale, d) for pc, w, d in slot.items) / tw
    return s * min(1.0, tw / 1.0)


def coverage(chord: Chord, slots, ivs_all=True) -> float:
    tw = sum(w for sl in slots for _, w, _ in sl.items)
    if tw <= 0:
        return 1.0
    return sum(w for sl in slots for pc, w, _ in sl.items if pc in chord.pcs) / tw


# ---- state space ---------------------------------------------------------------------------
def key_states(key: KeyCand):
    t = key.tonic
    if key.mode == "major":
        spec = [(0, "maj", .8), (2, "min", .1), (4, "min", -.3), (5, "maj", .5), (7, "maj", .5),
                (9, "min", .3), (10, "maj", -.6), (5, "min", -.9)]
    else:
        spec = [(0, "min", .8), (3, "maj", .3), (5, "min", .5), (7, "min", -.2), (7, "maj", .2),
                (8, "maj", .3), (10, "maj", .3)]
    return [(Chord((t + d) % 12, q), p) for d, q, p in spec]


_INTERVAL = {7: .6, 5: .4, 2: .3, 9: .3, 4: .0, 3: .0, 10: .2, 8: .0, 1: -.5, 6: -.5, 11: -.3}


def transition(a: Chord, b: Chord, key: KeyCand, mid_bar: bool) -> float:
    if a == b:
        return 0.0
    s = _INTERVAL.get((b.root - a.root) % 12, 0.0)
    s += 0.15 * len(a.core & b.core)
    dom = (key.tonic + 7) % 12
    if a.root == dom and b.root == key.tonic:
        s += 0.5
    if a.root == dom and b.root == (key.tonic + 5) % 12:
        s -= 0.4
    return s - (1.0 if mid_bar else 0.7)


def _emission(chord, prior, slot: Slot, key: KeyCand, scale):
    e = 3.0 * fit(chord, slot, scale) + prior - 0.3 * best_voicing(chord).difficulty / 2.0
    tonic_triad = (chord.root == key.tonic and (chord.quality == ("maj" if key.mode == "major" else "min")))
    dom = chord.root == (key.tonic + 7) % 12
    if slot.last and tonic_triad:
        e += 1.5
    if slot.phrase_end and not slot.last:
        e += 0.5 if (tonic_triad or dom) else 0.0
    return e


def decode(slots, key: KeyCand, bpb: int):
    states = key_states(key)
    scale = key.scale
    K, N = len(states), len(slots)
    E = np.array([[_emission(c, p, sl, key, scale) for c, p in states] for sl in slots])
    # reward tonic on the opening slot a little
    for k, (c, _) in enumerate(states):
        if c.root == key.tonic and c.quality == ("maj" if key.mode == "major" else "min"):
            E[0, k] += 0.5
    T = {m: np.array([[transition(a, b, key, m) for b, _ in states] for a, _ in states]) for m in (False, True)}
    dp = np.full((N, K), -1e9)
    bp = np.zeros((N, K), dtype=int)
    dp[0] = E[0]
    for i in range(1, N):
        tm = T[not slots[i].bar_start]
        cand = dp[i - 1][:, None] + tm
        bp[i] = cand.argmax(0)
        dp[i] = cand.max(0) + E[i]
    path = [int(dp[-1].argmax())]
    for i in range(N - 1, 0, -1):
        path.append(int(bp[i][path[-1]]))
    path.reverse()
    return states, path, float(dp[-1].max()), E, T


def path_score(path, E, T, slots):
    s = E[0, path[0]]
    for i in range(1, len(path)):
        s += T[not slots[i].bar_start][path[i - 1], path[i]] + E[i, path[i]]
    return float(s)


# ---- progression + alternatives ------------------------------------------------------------
@dataclass
class ChordEvent:
    start_beat: float
    end_beat: float
    chord: Chord
    function: str
    confidence: float
    alternatives: list
    coverage: float


STYLE = {"add9": 0.0, "maj7": 0.02, "m7": 0.0, "7": 0.0, "sus4": 0.15, "sus2": 0.15}   # taste: prefer add9/7ths to sus
COLORS = {"maj": ["maj7", "add9", "sus4", "sus2"], "min": ["m7"]}


def select_progression(grid, notes, phrases, keys: list[KeyCand]):
    bpb = grid.beats_per_bar
    slot_beats = 2 if bpb == 4 else bpb
    slots = make_slots(grid, notes, phrases, slot_beats)
    if not slots:
        return None, []
    best = None
    for k in keys:
        states, path, sc, E, T = decode(slots, k, bpb)
        total = sc + 30.0 * k.score
        if best is None or total > best[0]:
            best = (total, k, states, path, E, T)
    _, key, states, path, E, T = best
    scale = key.scale
    # group runs of identical chords into events
    runs, a = [], 0
    for i in range(1, len(path) + 1):
        if i == len(path) or path[i] != path[a]:
            runs.append((a, i))
            a = i
    chosen = [states[path[a]][0] for a, _ in runs]
    base_total = path_score(path, E, T, slots)
    events = []
    for ri, (a, b) in enumerate(runs):
        ch = chosen[ri]
        sl = slots[a:b]
        alts = []
        # alternative roots/triads: re-score the whole path with this event substituted
        for k, (c2, _) in enumerate(states):
            if c2 == ch:
                continue
            p2 = list(path)
            p2[a:b] = [k] * (b - a)
            d = path_score(p2, E, T, slots) - base_total
            alts.append({"chord": c2.name, "kind": "substitute", "delta": round(d, 2),
                         "function": c2.roman(key.tonic),
                         "reason": f"covers {coverage(c2, sl):.0%} of melody weight (chosen {coverage(ch, sl):.0%})"})
        alts.sort(key=lambda x: -x["delta"])
        alts = alts[:3]
        # colour variants of the chosen chord
        nxt = chosen[ri + 1] if ri + 1 < len(chosen) else None
        base_fit = sum(fit(ch, s, scale) for s in sl)
        colors = []
        for q in (["7"] if (ch.quality == "maj" and ch.root == (key.tonic + 7) % 12) else []) + COLORS.get(ch.quality, []):
            v = Chord(ch.root, q)
            gain = sum(fit(v, s, scale) for s in sl) - base_fit
            extra = sorted(v.pcs - ch.pcs)
            held = sum(w for s in sl for pc, w, _ in s.items if pc in extra)
            reason = (f"adds {'/'.join(['C','Db','D','Eb','E','F','F#','G','Ab','A','Bb','B'][p] for p in extra)}; "
                      + (f"melody touches it ({held:.1f} wt)" if held > 0 else "colour only"))
            colors.append({"chord": v.name, "kind": "colour", "delta": round(0.8 * gain - 0.25 - STYLE.get(q, 0.0), 2),
                           "function": v.roman(key.tonic), "reason": reason, "_gain": gain, "_q": q})
        # automatic colour: V7 into the tonic; otherwise a colour only if melody clearly supports it
        final = ch
        v7 = [c for c in colors if c["_q"] == "7"]
        if (v7 and ch.root == (key.tonic + 7) % 12 and nxt is not None and nxt.root == key.tonic
                and v7[0]["_gain"] >= -0.05):
            final = Chord(ch.root, "7")
        else:
            sup = [c for c in colors if c["_gain"] >= 0.25 and c["_q"] != "7"]
            if sup:
                final = Chord(ch.root, max(sup, key=lambda c: c["_gain"] - STYLE.get(c["_q"], 0.0))["_q"])
        colors = [c for c in colors if c["chord"] != final.name]
        if final != ch:
            colors.append({"chord": ch.name, "kind": "colour", "delta": 0.0, "function": ch.roman(key.tonic),
                           "reason": "plain triad", "_gain": 0, "_q": ch.quality})
        for c in colors:
            c.pop("_gain"), c.pop("_q")
        colors.sort(key=lambda x: -x["delta"])
        alts = (alts + colors[:2])
        alts.sort(key=lambda x: -x["delta"])
        alts = alts[:4]
        z = 1.0 + sum(np.exp(min(0, x["delta"])) for x in alts if x["kind"] == "substitute")
        events.append(ChordEvent(slots[a].b0, slots[b - 1].b1, final, final.roman(key.tonic),
                                 round(float(1.0 / z), 2), alts,
                                 round(coverage(final, sl), 2)))
    return key, events
