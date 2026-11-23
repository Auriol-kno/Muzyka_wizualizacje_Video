"""J.S. Bach – Wariacje Goldbergowskie BWV 988, Aria. Transkrypcja z dostarczonego zapisu nutowego
(Open Goldberg Variations, domena publiczna). Ozdobniki rozpisane (przednutki, mordenty, tryle),
głosy środkowe miejscami uproszczone. Forma: ||: 1–16 :||: 17–32 :|| (64 takty).
Kanał 0 = górny głos (melodia), kanał 1 = pozostałe głosy.
"""
import os
import re
import sys as _sys
from pathlib import Path as _Path
ROOT = _Path(__file__).resolve().parents[2]
_sys.path.insert(0, str(ROOT / "wspolne"))
from midi_io import write_midi

PPQ = 480
BPM = 62
NB = {"C": 0, "D": 2, "E": 4, "F": 5, "G": 7, "A": 9, "B": 11}
GMAJ = {0, 2, 4, 6, 7, 9, 11}


def n(s):
    m = re.fullmatch(r"([A-G])([#bn]?)(-?\d)", s)
    v = NB[m.group(1)] + {"#": 1, "b": -1, "n": 0, "": 0}[m.group(2)]
    if m.group(1) == "F" and m.group(2) == "":
        v += 1  # znak przykluczowy: Fis
    return 12 * (int(m.group(3)) + 1) + v


def upper(p):
    q = p + 1
    while q % 12 not in GMAJ:
        q += 1
    return q


# takt: [głos0 (melodia), głos1, ...]   zapis: Nuta:długość[p|t]  (p = mordent górny, t = tryl)
A = {
    1: ["G5:1 G5:1 A5:.75p B5:.25", "r:1 B3:1 D4:1", "G3:3"],
    2: ["A5:.5 G5:.25 F5:.25 E5:1 D5:1", "r:1 A3:1 D4:1", "F3:3"],
    3: ["G4:1p G4:1.5t F4:.25 G4:.25", "r:1 G3:1 C#4:1", "E3:3"],
    4: ["A4:.25 G4:.125 F4:.125 G4:.25 F4:.125 E4:.125 E4:.5 D4:1.5", "r:1 F3:1 A3:1", "D3:2.5 C3:.5"],
    5: ["D5:1 D5:1 E5:.75p Fn5:.25", "r:1 D3:1 G3:1", "B2:3"],
    6: ["E5:.5 D5:.25 C5:.25 B4:.5 A4:1 F5:.5", "r:1 E3:1 A3:1", "C3:2.5 D3:.5"],
    7: ["G5:.125 F5:.375 A5:.125 G5:.375 F5:.125 E5:.375 D5:.125 C5:.375 C5:.25 A5:.5 C5:.25",
        "r:.5 C4:1 B3:.25 A3:.25 G3:.25 F3:.25 E3:.25 F3:.25", "E3:.5 C3:.5 D3:2"],
    8: ["B4:.125 G4:.375 F4:.5 F4:.5 G4:1.5p", "G3:.5 A3:.5 B3:2", "G2:1.5 D3:.5 E3:.75p F3:.25"],
    9: ["B4:1 B4:1 C#5:.75p D5:.25", "r:1 B3:1 E4:1", "G3:3"],
    10: ["D5:.25 C#5:.25 B4:.25 A4:.25 D5:2", "A3:1 r:2", "G3:1 F3:.5t E3:.5 F3:.5 B3:.5", "r:1 A4:2"],
    11: ["G5:1 G5:1.5t F5:.25 G5:.25", "B4:1 r:2", "r:.5 B3:.5 E4:1.5 D4:.5", "E3:1.5 E3:.5 F3:.5 G3:.5", "E5:1 r:2"],
    12: ["G5:.5 F5:.25 E5:.25 C#5:1.5t E5:.5", "C#4:.5 D4:.5 E4:2", "A3:1.5 B3:.5 A3:.5 G3:.5"],
    13: ["A5:.25 G5:.25 F5:.25 E5:.25 D5:.5 A4:1.25 B4:.125 C5:.125", "r:1 A3:1 D4:1", "F3:3"],
    14: ["B4:.25 A4:.25 G4:.25 F4:.25 E4:.5 D5:.25 C#5:1 D5:.125 E5:.125", "r:1 B3:1 E4:1", "G3:3"],
    15: ["D5:.25 C#5:.25 B4:.25 A4:.25 G5:.5 B4:1 C#5:.5", "F4:1 E4:.75 F4:.25 G4:1", "A3:3"],
    16: ["D5:1.25 E5:.125 D5:.125 C#5:.5 D5:1", "G4:1 F4:2", "r:1.5 A3:.5 D4:1", "D3:3"],
    17: ["A4:1p A4:1.25t A4:.25 B4:.125 C5:.125 D5:.125 E5:.125", "r:.5 E4:.5 F4:2p", "D4:2 C4:1"],
    18: ["E5:.25 D5:.25 C5:.25 B4:.25 A4:.5 G4:1 G5:.5", "r:.5 C4:.5 D4:2", "B3:1.5 A3:.5 B3:1"],
    19: ["F5:.25 E5:.5 F5:.125 D#5:.125 D#5:.25 E5:1.25p F5:.125 G5:.125 F5:.125 E5:.125",
         "r:.5 E4:.5 G4:1 F4:.5p E4:.5", "C4:1.5 B3:.5 A3:1"],
    20: ["A5:.75 F5:.25 E5:.25 D#5:1.25 B4:.5", "D#4:.5 E4:.5 F4:2", "B3:1.5 A3:.5 G3:.5 F3:.5"],
    21: ["G5:.75t F5:.25 E5:1.25 B4:.25 C5:.125 B4:.125 A4:.125 B4:.125", "r:.5 A3:1 G3:.5t F3:.5 G3:.5", "C3:2 D3:1"],
    22: ["G5:.125 F5:.375 F5:.125 D#5:.375 E5:1.25 G4:.25 F4:.25 E4:.25", "r:.5 A3:.5 G3:.5t F3:.5 G3:.5 B3:.5", "C3:2 B2:1"],
    23: ["E5:1 D#5:.5 A5:.5 G5:.5 F5:.5", "F4:1.5 C5:.5 B4:.5 A4:.5", "A2:.5 C3:.5 B2:.5 A2:.5 B2:.5 D#3:.5"],
    24: ["E5:.75 F5:.125 D#5:.125 D#5:.25 E5:1.75", "A4:1 G4:2", "E3:.5 B2:.5 E2:.5 B2:.5 E3:.5 Dn3:.5"],
    25: ["E5:.5 D5:.25 C5:.25 B4:.5 A4:1 B4:.25 C5:.25", "r:1 E3:1 A3:1", "C3:3"],
    26: ["D5:.125 C5:.125 B4:.25 C5:.125 B4:.125 A4:.25 A4:.25 G4:1.25 A4:.25 B4:.25",
         "A3:.5 F3:.5 D3:.5 E3:.25 F3:.25 G3:.25 F3:.25 G3:.5", "B2:3"],
    27: ["C5:.25 D5:.25 C5:.25 B4:.25 C5:.25 A4:.25 F4:.25 A4:.25 C5:1", "r:1.5 E4:.5 B4:.25 A4:.25 G4:.5",
         "G3:.5 E3:.5 A3:.5 r:1.5", "A2:1.5 G2:.5 F2:.5 E2:.5"],
    28: ["C5:.25 D5:.25 C5:.25 B4:.25 C5:.25 A4:.25 F4:.25 A4:.25 C5:.25 E5:.25 D5:.25 C5:.25",
         "F4:1 r:.5 F4:1.5", "D2:.5 A2:.5 D3:.5 C3:.5 B2:.5 A2:.5"],
    29: ["B4:.25 C5:.25 B4:.25 A4:.25 B4:.25 G4:.25 D4:.25 G4:.25 B4:.25 G4:.25 C5:.25 D5:.25",
         "G4:.5 r:.5 r:.5 D4:.75 G4:.75", "G2:.5 D3:.5 G3:.5 Fn3:.5 E3:.5 D3:.5"],
    30: ["E5:.25 Fn5:.25 E5:.25 D5:.25 E5:.25 C5:.25 G4:.25 C5:.25 E5:.25 C5:.25 F5:.25 G5:.25",
         "G4:1 r:.5 G4:.75 C5:.75", "C3:.5 G3:.5 C4:.5 B3:.5 A3:.5 G3:.5"],
    31: ["A5:.25 C5:.25 B4:.25 A4:.25 B4:.25 C5:.25 D5:.25 G4:.25 B4:.25 A4:.25 G4:.25 F4:.25",
         "F3:.5 D3:.5 G3:.5 B3:.5 D4:.5 D3:.5"],
    32: ["G4:1.25 G4:.25 F4:.5 G4:1", "r:.25 C4:.25 B3:.25 A3:.25 B3:1 r:1", "G3:1.5 D3:.5 G2:1"],
}
ORDER = list(range(1, 17)) * 2 + list(range(17, 33)) * 2
SECTIONS = {1: "A (t. 1)", 17: "A powt. (t. 1)", 33: "B (t. 17)", 49: "B powt. (t. 17)"}
BASEV = [70, 50, 56, 50, 50]


def build():
    T = lambda b: int(round(b * PPQ))
    mel, acc = [], []
    for k, bar in enumerate(ORDER, start=1):
        b0 = 3 * k
        voices = A[bar]
        for vi, spec in enumerate(voices):
            o = 0.0
            toks = spec.split()
            for ti, tok in enumerate(toks):
                p, d = tok.split(":")
                orn = d[-1] if d[-1] in "pt" else ""
                d = float(d.rstrip("pt"))
                if p != "r":
                    pitch = n(p)
                    v = BASEV[min(vi, 4)] + (6 if abs(o - 1) < 1e-6 else 0) + (4 if abs(o) < 1e-6 else 0)
                    if vi == 0:
                        v += int((pitch - 74) * 0.5)
                    if k == 64:
                        v -= 6
                    seg = []
                    if orn == "p" and d >= 0.5:
                        u = upper(pitch)
                        seg = [(0, .125, pitch), (.125, .125, u), (.25, d - .25, pitch)]
                    elif orn == "t" and d >= 0.75:
                        u = upper(pitch); q = 0.0; s = 0; L = d * 0.65
                        while q < L - 1e-9:
                            seg.append((q, .125, u if s % 2 == 0 else pitch)); q += .125; s += 1
                        seg.append((q, d - q, pitch))
                    else:
                        seg = [(0, d, pitch)]
                    dst = mel if vi == 0 else acc
                    for so, sd, sp in seg:
                        art = 0.96 if sd < 1 else 0.98
                        end = b0 + o + so + sd * art
                        if k == 64 and ti == len(toks) - 1:
                            end = b0 + o + so + sd + 2.0  # ostatni akord wybrzmiewa
                        dst.append((T(b0 + o + so), T(end), sp, max(35, min(110, v - (8 if sp != pitch else 0)))))
                o += d
            assert abs(o - 3) < 1e-6, (bar, vi, o)
    tempo = [(0, int(60e6 / BPM))]
    tot = 3 * (len(ORDER) + 1)
    for i, bpm in enumerate([58, 55, 52, 49, 46, 42]):
        tempo.append((T(tot - 6 + i), int(60e6 / bpm)))
    markers = [(T(3 * k), lab) for k, lab in SECTIONS.items()]
    return [("Melodia", 0, mel), ("Glosy", 1, acc)], tempo, markers


if __name__ == "__main__":
    here = os.path.dirname(os.path.abspath(__file__))
    out = os.path.join(here, "Bach_Goldberg_Aria_BWV988.mid")
    tr, tempo, mk = build()
    write_midi(out, tr, PPQ, tempo, (3, 4), mk, "J.S. Bach - Goldberg Variations - Aria")
    print("zapisano", out, sum(len(t[2]) for t in tr), "nut")
