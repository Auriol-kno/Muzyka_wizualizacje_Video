"""Prosty odczyt główek nut (wysokości) z zapisu nutowego – pomoc przy ręcznej transkrypcji."""
import sys
import numpy as np
from PIL import Image
from scipy import ndimage as ndi

NAMES = "CDEFGAB"


def lines_of(a):
    rows = (a).mean(1)
    ys = np.nonzero(rows > 0.5)[0]
    g = []
    for y in ys:
        if g and y - g[-1][-1] <= 2:
            g[-1].append(y)
        else:
            g.append([y])
    c = [float(np.mean(x)) for x in g]
    st, i = [], 0
    while i + 4 < len(c):
        d = np.diff(c[i:i + 5])
        if d.max() - d.min() < 3 and 10 < d.mean() < 40:
            st.append(c[i:i + 5]); i += 5
        else:
            i += 1
    return st


def name(di):
    return NAMES[di % 7] + str(di // 7)


def analyse(path, page):
    a = np.asarray(Image.open(path).convert("L")) < 140
    st = lines_of(a)
    sp = np.mean([np.diff(s).mean() for s in st])
    b = a.copy()
    # usuń linie pięciolinii
    for s in st:
        for y in s:
            for yy in range(int(y) - 1, int(y) + 2):
                above = a[yy - 2] if yy - 2 >= 0 else 0
                below = a[yy + 2]
                b[yy] = b[yy] & (above | below) & False | (b[yy] & above & below)
    filled = ndi.binary_fill_holes(b)
    k = np.zeros((int(sp * 0.75), int(sp * 0.95)), bool)
    yy, xx = np.mgrid[0:k.shape[0], 0:k.shape[1]]
    k = ((yy - k.shape[0] / 2 + .5) / (k.shape[0] / 2)) ** 2 + ((xx - k.shape[1] / 2 + .5) / (k.shape[1] / 2)) ** 2 <= 1
    heads = ndi.binary_opening(filled, structure=k)
    lab, n = ndi.label(heads)
    objs = ndi.find_objects(lab)
    cents = ndi.center_of_mass(heads, lab, range(1, n + 1))
    res = []
    for j in range(0, len(st) - 1, 2):
        tr, bs = st[j], st[j + 1]
        # kreski taktowe: kolumny czarne przez całą wysokość obu pięciolinii
        col = a[int(tr[0]):int(bs[-1]) + 1].mean(0)
        bars = np.nonzero(col > 0.97)[0]
        bl = []
        for x in bars:
            if not bl or x - bl[-1][-1] > 3:
                bl.append([x])
            else:
                bl[-1].append(x)
        bl = [int(np.mean(x)) for x in bl]
        notes = []
        for (cy, cx), o in zip(cents, objs):
            h, w = o[0].stop - o[0].start, o[1].stop - o[1].start
            if not (0.6 * sp < h < 2.6 * sp and 0.7 * sp < w < 2.2 * sp):
                continue
            for staff, top, nm in ((tr, 38, "R"), (bs, 26, "L")):
                if staff[0] - 6 * sp < cy < staff[-1] + 6 * sp:
                    # rozdzielenie ewentualnych akordów pionowych (wysoka główka = 2 nuty)
                    nheads = max(1, int(round(h / (sp * 0.95))))
                    for q in range(nheads):
                        yq = o[0].start + (q + 0.5) * h / nheads
                        di = top - int(round((yq - staff[0]) / (sp / 2)))
                        notes.append((nm, cx, name(di)))
        res.append((bl, notes))
    return res


if __name__ == "__main__":
    for page in sys.argv[1:]:
        for si, (bl, notes) in enumerate(analyse(page, 0)):
            print(f"== {page} system {si + 1}: kreski {bl}")
            for hand in "RL":
                segs = []
                edges = [0] + bl + [10 ** 6]
                for k in range(len(edges) - 1):
                    xs = sorted([(cx, nm) for h_, cx, nm in notes if h_ == hand and edges[k] <= cx < edges[k + 1]])
                    if xs:
                        segs.append(" ".join(f"{nm}@{int(cx)}" for cx, nm in xs))
                print(hand, " || ".join(segs))
