"""Fryderyk Chopin – Walc a-moll, B.150 (KK IVb nr 11), Allegretto, 3/4.
Transkrypcja z zapisu nutowego dostarczonego przez użytkownika (domena publiczna).
Uproszczenia: tryle i mordenty zagrane jako zwykłe nuty, przednutki jako krótkie nuty przed miarą,
pasaż w t. 21 uproszczony. Forma z powtórzeniami: 1–16, 17–24 ×2, 25–40 ×2, 41–56 (80 taktów).
"""
import os
import re
import sys as _sys
from pathlib import Path as _Path
ROOT = _Path(__file__).resolve().parents[2]
_sys.path.insert(0, str(ROOT / "wspolne"))
from midi_io import write_midi

PPQ = 480
BPM = 138
NAMES = {"C": 0, "D": 2, "E": 4, "F": 5, "G": 7, "A": 9, "B": 11}


def n(s):
    m = re.fullmatch(r"([A-G])([#b]?)(-?\d)", s)
    v = NAMES[m.group(1)] + {"#": 1, "b": -1, "": 0}[m.group(2)]
    return 12 * (int(m.group(3)) + 1) + v


def mel(spec):
    """'A4:e B4:e C5:q r:q' -> [(offset_beats, dur_beats, pitch|None)]"""
    D = {"s": .25, "e": .5, "q": 1, "h": 2, "dh": 3, "t": 1 / 3, "f": 1 / 5}
    out, o = [], 0.0
    for tok in spec.split():
        p, d = tok.split(":")
        d = D[d]
        out.append((o, d, None if p == "r" else n(p)))
        o += d
    assert abs(o - 3) < 1e-6 or abs(o - 1) < 1e-6, (spec, o)
    return out


Am, Dm, G7, C, E7 = ["A3", "C4", "E4"], ["F3", "A3", "D4"], ["B3", "D4", "F4"], ["G3", "C4", "E4"], ["G#3", "B3", "D4"]
A, B7, Ema, F_C = ["A3", "C#4", "E4"], ["A3", "D#4", "F#4"], ["G#3", "B3", "E4"], ["F3", "A3", "C4"]

# takt: (melodia, bas, akord, wzór, przednutka)   wzór: 3 = akord na 2 i 3, 2 = akord tylko na 2
BAR = {
    1: ("A4:e B4:e C5:q C5:q", "A1", Am, 3, None),
    2: ("D5:e E5:e F5:h", "D2", Dm, 3, None),
    3: ("B4:e C5:e D5:e A5:e G5:e F5:e", "G2", G7, 3, None),
    4: ("E5:e D#5:e E5:h", "C3", C, 3, "F5"),
    5: ("A4:e B4:e C5:q C5:q", "A2", Am, 3, None),
    6: ("D5:e E5:e F5:h", "D2", Dm, 3, None),
    7: ("B4:e C5:e D5:e A5:e G5:e B4:e", "G2", G7, 3, None),
    8: ("C5:q r:q E4:q", "C3", C, 2, None),
    9: ("A4:e B4:e C5:q C5:q", "A1", Am, 3, None),
    10: ("D5:e E5:e F5:h", "D2", Dm, 3, None),
    11: ("B4:e C5:e D5:e A5:e G5:e F5:e", "G2", G7, 3, None),
    12: ("E5:e D#5:e E5:h", "C3", C, 3, "F5"),
    13: ("C5:e D5:e E5:q E5:q", "A2", Am, 3, None),
    14: ("F5:e G5:e A5:h", "D2", Dm, 3, None),
    15: ("G5:q F#5:e G5:e D6:e F5:e", "G2", G7, 3, None),
    16: ("E5:dh", "C3", C, 3, None),
    17: ("E5:e F#5:e G#5:e A5:e B5:e C6:e", "E2", E7, 3, None),
    18: ("C6:e A5:e E5:e B5:e A5:q", "A2", Am, 3, "D6"),
    19: ("A5:e G#5:e E5:e F#5:e E5:q", "E2", E7, 3, "B5"),
    20: ("E5:e C5:e A4:e B4:e A4:q", "A2", Am, 3, "F5"),
    21: ("E4:t G#4:t B4:t E5:f F#5:f G#5:f A5:f B5:f E6:e B6:e", "E2", E7, 3, None),
    22: ("C7:e A6:e E6:e B6:e A6:q", "A2", Am, 3, "D7"),
    23: ("A6:e G#6:e E6:e F#6:e E6:q", "E2", E7, 3, "B6"),
    24: ("A6:h r:q", "A2", Am, 3, None),
    29: ("C5:e D5:e E5:q E5:q", "A2", Am, 3, None),
    30: ("F5:e G5:e A5:h", "D2", Dm, 3, None),
    31: ("D#5:e E5:e F#5:q F#5:q", "B1", B7, 3, None),
    32: ("G#5:e A5:e B5:h", "E2", Ema, 2, None),
    33: ("B5:e C#6:e D6:e D#6:e E6:e D6:e", "E2", A, 3, None),
    34: ("C#6:e B5:e C#6:e G#5:e A5:e F#5:e", "A2", A, 3, None),
    35: ("E5:e D5:e G#4:e F#5:e E5:q", "E2", E7, 3, "F#5"),
    36: ("E5:e C#5:e A4:e F#5:e E5:q", "A2", A, 3, "F#5"),
    39: ("E5:e D5:e G#4:e F#5:e E5:e G#4:e", "E2", E7, 3, "F#5"),
    40: ("A4:q r:q E4:q", "A2", A, 2, None),
    51: ("r:e E5:e D#5:e E5:e B5:e D5:e", "E2", E7, 3, None),
    52: ("C5:h r:q", "A2", Am, 3, None),
    53: ("r:e C6:e B5:e A5:e G5:e F5:e", "C3", F_C, 2, None),
    54: ("E5:e D5:e C#5:e D5:e E5:e F5:e", "D2", Dm, 2, None),
    55: ("E5:q D#5:e E5:e F5:e G#4:e", "E2", E7, 3, None),
    56: ("A4:h r:q", "A2", Am, 2, None),
}
for k, src in {25: 1, 26: 2, 27: 3, 28: 4, 37: 33, 38: 34, 41: 1, 42: 2, 43: 3, 44: 4, 45: 5, 46: 6,
               47: 7, 48: 8, 49: 1, 50: 2}.items():
    BAR[k] = BAR[src]
BAR[25] = ("A4:e B4:e C5:q C5:q", "A1", Am, 3, None)

ORDER = list(range(1, 17)) + list(range(17, 25)) * 2 + list(range(25, 41)) * 2 + list(range(41, 57))
SECTIONS = {1: "A", 17: "B", 33: "C", 65: "D"}
SECTIONS = {1: "A (t. 1)", 17: "B (t. 17)", 25: "B powt. (t. 17)", 33: "C (t. 25)", 49: "C powt. (t. 25)", 65: "D (t. 41)"}
DYN = {"A": 80, "B": 88, "C": 72, "D": 80}


def section_of(k):
    lab = "A"
    for s, l in SECTIONS.items():
        if k >= s:
            lab = l[0]
    return lab


def build():
    T = lambda beats: int(round(beats * PPQ))
    mel_notes, acc = [], []
    # przedtakt: E4 na 3. miarę taktu 0
    mel_notes.append((T(2), T(2.95), n("E4"), 70))
    for k, bar in enumerate(ORDER, start=1):
        spec, bass, chord, pat, grace = BAR[bar]
        b0 = 3 * k
        base = DYN[section_of(k)]
        if k >= 79:
            base -= 8
        evs = mel(spec)
        if grace:
            first = next(e for e in evs if e[2] is not None)
            mel_notes.append((T(b0 + first[0] - 0.14), T(b0 + first[0] - 0.01), n(grace), base - 12))
        for i, (o, d, p) in enumerate(evs):
            if p is None:
                continue
            last_in_bar = all(e[2] is None for e in evs[i + 1:])
            art = 0.97 if d < 1 else (0.86 if d == 1 and not last_in_bar else 0.95)
            v = base + int((p - 76) * 0.6) + (6 if o == 0 else 0)
            if bar == 56:
                d = 3.2  # wybrzmienie końcowego A
            mel_notes.append((T(b0 + o), T(b0 + o + d * art), p, max(40, min(118, v))))
        acc.append((T(b0), T(b0 + 2.4), n(bass), base - 20))
        for beat in ((1, 2) if pat == 3 else (1,)):
            for q in chord:
                acc.append((T(b0 + beat), T(b0 + beat + 0.8), n(q), base - 36 - 3 * (beat - 1)))
        if bar == 56:
            for q in chord:  # ostatni akord wybrzmiewa
                acc[-len(chord):] = [(T(b0 + 1), T(b0 + 4.2), n(q), base - 34) for q in chord]
            acc.append((T(b0), T(b0 + 4.5), n(bass) + 12, base - 30))
    total_beats = 3 * (len(ORDER) + 1)
    us = 60e6 / BPM
    tempo = [(0, int(us))]
    rit = [132, 126, 118, 110, 102, 94]  # ritardando w dwóch ostatnich taktach
    for i, bpm in enumerate(rit):
        tempo.append((T(total_beats - 6 + i), int(60e6 / bpm)))
    markers = [(T(3 * k), lab) for k, lab in SECTIONS.items()]
    return [("Melodia", 0, mel_notes), ("Akompaniament", 1, acc)], tempo, markers


if __name__ == "__main__":
    here = os.path.dirname(os.path.abspath(__file__))
    out = os.path.join(here, "Chopin_Walc_a-moll_B150.mid")
    tracks, tempo, markers = build()
    write_midi(out, tracks, PPQ, tempo, (3, 4), markers, "Chopin - Walc a-moll B.150")
    print("zapisano", out, sum(len(t[2]) for t in tracks), "nut")
