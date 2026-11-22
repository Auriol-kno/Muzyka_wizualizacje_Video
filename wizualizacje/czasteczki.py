"""Renderer cząsteczkowy offline (numpy/OpenCV): kamera perspektywiczna, rozpryskiwanie drobin,
głębia ostrości w warstwach, poświata. Pięć presetów – interpretacja artystyczna cech z `analiza.py`.

Zasada: pomiar (analiza.py) jest oddzielony od interpretacji (funkcje preset_*). Każdy preset zwraca
cząstki oraz słownik `parametry` – dokładnie te liczby, które sterowały obrazem (trafiają do manifestu).
Losowość: np.random.default_rng(seed) – ta sama para klatek ma ten sam seed, kamerę, paletę i skalę.
"""
import math
from fractions import Fraction

import cv2
import numpy as np
from scipy.ndimage import map_coordinates

cv2.setNumThreads(2)
W, H = 1920, 1080


def rgb(h):
    return np.array([int(h[i:i + 2], 16) / 255 for i in (1, 3, 5)], np.float32)


# ----------------------------------------------------------------------------- kamera i rozpryskiwanie
class Kamera:
    def __init__(self, pos, cel, ogniskowa=1.35):
        self.pos = np.array(pos, float)
        f = np.array(cel, float) - self.pos; f /= np.linalg.norm(f)
        r = np.cross(f, [0, 0, 1.0]); r /= np.linalg.norm(r)
        self.f, self.r, self.u = f, r, np.cross(r, f)
        self.F = ogniskowa * W / 2
        self.ostrosc = float(np.linalg.norm(np.array(cel, float) - self.pos))

    def rzut(self, P):
        rel = P - self.pos
        z = rel @ self.f
        z = np.maximum(z, 1e-4)
        return W / 2 + self.F * (rel @ self.r) / z, H / 2 - self.F * (rel @ self.u) / z, z


def splat(P, C, kam, jasnosc=1.0, warstwy=3, glebia=0.45):
    """P: (N,3) świat, C: (N,3) kolor*waga. Zwraca obraz emisji (H,W,3) z głębią ostrości."""
    sx, sy, z = kam.rzut(P)
    ok = (sx >= 0) & (sx < W - 1) & (sy >= 0) & (sy < H - 1) & (z > 0.05)
    sx, sy, z, C = sx[ok], sy[ok], z[ok], C[ok]
    C = C * (jasnosc * (kam.ostrosc / z) ** 1.2)[:, None]       # bliższe drobiny wyraźniejsze
    rozmycie = np.abs(np.log(z / kam.ostrosc))                    # odległość od płaszczyzny ostrości
    kraw = np.quantile(rozmycie, np.linspace(0, 1, warstwy + 1)) if len(z) else np.zeros(warstwy + 1)
    out = np.zeros((H, W, 3), np.float32)
    for k in range(warstwy):
        m = (rozmycie >= kraw[k]) & (rozmycie <= kraw[k + 1] + 1e-9)
        if not m.any():
            continue
        x, y, c = sx[m], sy[m], C[m]
        x0 = np.floor(x).astype(np.int64); y0 = np.floor(y).astype(np.int64)
        fx = (x - x0).astype(np.float32); fy = (y - y0).astype(np.float32)
        acc = np.zeros((3, H * W), np.float64)
        for dx, dy, w in ((0, 0, (1 - fx) * (1 - fy)), (1, 0, fx * (1 - fy)), (0, 1, (1 - fx) * fy), (1, 1, fx * fy)):
            idx = (y0 + dy) * W + (x0 + dx)
            for ch in range(3):
                acc[ch] += np.bincount(idx, weights=c[:, ch] * w, minlength=H * W)
        lay = acc.reshape(3, H, W).transpose(1, 2, 0).astype(np.float32)
        sig = glebia * (kraw[k] + kraw[k + 1]) / 2 * 6
        if sig > 0.35:
            lay = cv2.GaussianBlur(lay, (0, 0), sig)
        out += lay
    return out


def kompozycja(tlo, emisja, ekspozycja=1.0, poswiata=0.35, ziarno=0.006, seed=0):
    e = emisja * ekspozycja
    q = cv2.resize(e, (W // 4, H // 4), interpolation=cv2.INTER_AREA)
    bl = cv2.resize(cv2.GaussianBlur(q, (0, 0), 6), (W, H)) + 0.5 * cv2.resize(cv2.GaussianBlur(q, (0, 0), 18), (W, H))
    img = tlo + 1 - np.exp(-(e + poswiata * bl))
    rng = np.random.default_rng(seed + 99)
    img += (rng.random((H, W, 1), np.float32) - 0.5) * ziarno
    return np.clip(img, 0, 1)


def tlo_gradient(gora, dol, winieta=0.45, swiatlo=None):
    yy, xx = np.mgrid[0:H, 0:W].astype(np.float32)
    v = (yy / H)[..., None]
    img = gora * (1 - v) + dol * v
    d = ((xx - W / 2) / (W / 2)) ** 2 + ((yy - H / 2) / (H / 2)) ** 2
    img = img * (1 - winieta * np.clip(d / 2, 0, 1))[..., None]
    if swiatlo is not None:
        cx, cy, r, c = swiatlo
        img += c * np.exp(-(((xx - cx * W) / (r * W)) ** 2 + ((yy - cy * H) / (r * W)) ** 2))[..., None]
    return img.astype(np.float32)


def szum(rng, skala, n=64):
    """Deterministyczny gładki szum (wartości losowe na siatce, interpolacja sześcienna)."""
    siatka = rng.standard_normal((n, n)).astype(np.float32)

    def f(x, y):
        # "grid-wrap" = okres dokładnie n, gładko przez krawędź; dawne mod(n−1) + "wrap" dawało szew przy x = 0
        return map_coordinates(siatka, [np.mod(y * skala, n), np.mod(x * skala, n)], order=3, mode="grid-wrap")
    return f


# ----------------------------------------------------------------------------- 1. cymatyka – złoty piasek
def preset_cymatyka(c, t, rng):
    """Inspiracja figurami Chladniego (nie fizyczny model płyty): ziarna gromadzą się na liniach węzłowych
    rozet sin(k·π·r)·cos(n·θ). Każdy silny szczyt widma (do 4) daje jedną rozetę; n i k wynikają
    z wysokości szczytu (półton → liczby całkowite). Energia → liczba ziaren i ostrość linii,
    atak → podskok ziaren, wysokie pasmo → drobny pył."""
    kam = Kamera((0, -2.05, 1.55), (0, 0.08, 0))
    E = c["energia"]
    sz = [s for s in c["szczyty"] if s[1] > 0.12]
    K = 0 if E < 0.03 else max(1, min(4, max(c["wielodzwiek"], 1), len(sz)))
    Ps, Cs, mody = [], [], []
    zloto, krem = rgb("#E3A93C"), rgb("#F4E7C6")
    for k in range(K):
        f, a = sz[k]
        s = int(round(12 * math.log2(f / 55.0)))
        n = 2 + s % 6
        kk = 2.0 + (s // 6) % 5 * 1.3
        mody.append(dict(f_hz=f, sila=a, n=n, k=round(kk, 2)))
        N = int(90_000 + 900_000 * E * a)
        r = np.sqrt(rng.random(N * 4)); th = rng.random(N * 4) * 2 * np.pi
        F = np.sin(kk * np.pi * r) * np.cos(n * th + 0.7 * k)
        sig = 0.10 - 0.06 * min(1, E)
        keep = rng.random(N * 4) < np.exp(-(F / sig) ** 2)
        r, th = r[keep][:N], th[keep][:N]
        x, y = 0.95 * r * np.cos(th), 0.95 * r * np.sin(th)
        jump = (rng.random(len(r)) < 0.35) * rng.exponential(0.018 + 0.06 * c["impuls_ataku"], len(r)) * c["impuls_ataku"]
        P = np.stack([x, y, jump], 1)
        mix = rng.random((len(r), 1))
        col = (zloto * (1 - mix) + krem * mix) * (0.55 + 0.45 * rng.random((len(r), 1))) * (0.9 - 0.12 * k)
        Ps.append(P); Cs.append(col * 0.11)
    # pył na całej płycie (zawsze trochę, więcej przy wysokim paśmie)
    Nd = int(25_000 + 120_000 * c["wysokie"])
    r = np.sqrt(rng.random(Nd)); th = rng.random(Nd) * 2 * np.pi
    Ps.append(np.stack([0.97 * r * np.cos(th), 0.97 * r * np.sin(th), np.zeros(Nd)], 1))
    Cs.append(np.tile(krem * 0.025, (Nd, 1)))
    # krawędź płyty
    th = rng.random(40_000) * 2 * np.pi
    Ps.append(np.stack([0.985 * np.cos(th), 0.985 * np.sin(th), np.zeros(40_000)], 1))
    Cs.append(np.tile(zloto * 0.05, (40_000, 1)))
    em = splat(np.vstack(Ps), np.vstack(Cs), kam)
    tlo = tlo_gradient(rgb("#0B0A0D"), rgb("#141012"), swiatlo=(0.5, 0.55, 0.35, rgb("#1E160C")))
    return kompozycja(tlo, em, 1.25, 0.30), dict(liczba_rozet=K, rozety=mody, ostrosc_linii=round(0.10 - 0.06 * min(1, E), 3),
                                                  podskok_ziaren=round(c["impuls_ataku"], 3))


# ----------------------------------------------------------------------------- 2. ocean harmonicznych
def preset_ocean(c, t, rng):
    """Powierzchnia z drobin. Dominująca fala ← najsilniejszy szczyt widma (zwykle melodia): długość fali
    maleje z wysokością dźwięku, amplituda ∝ energia. Pozostałe szczyty (mieszanina dźwięków i alikwotów)
    → drobniejsze fale w innych kierunkach. Atak → krąg zmarszczki. Cisza → prawie płaska tafla."""
    kam = Kamera((0, -1.05, 0.95), (0, 2.1, 0))
    E = c["energia"]
    sz = c["szczyty"] or [(440.0, 0.0)]
    N = 1_500_000
    x = (rng.random(N) * 2 - 1) * (0.5 + 2.3 * rng.random(N) ** 0.5)
    y = 0.15 + 4.8 * rng.random(N) ** 1.6
    f1 = sz[0][0]
    lam0 = 0.55 * (440.0 / f1) ** 0.5
    A0 = 0.11 * E
    d0 = np.array([0.35, 1.0]); d0 /= np.linalg.norm(d0)
    h = A0 * np.sin(2 * np.pi * (x * d0[0] + y * d0[1]) / lam0 - 1.3 * t)
    fale = [dict(f_hz=round(f1, 1), dlugosc=round(lam0, 3), amplituda=round(A0, 4), rola="dominująca")]
    for i, (f, a) in enumerate(sz[1:6], 1):
        lam = max(0.04, lam0 * (f1 / f) ** 0.7 * 0.75)
        A = 0.045 * a * E
        ang = 0.9 * i + 0.3
        h += A * np.sin(2 * np.pi * (x * math.cos(ang) + y * math.sin(ang)) / lam - (1.7 + 0.3 * i) * t)
        fale.append(dict(f_hz=round(f, 1), dlugosc=round(lam, 3), amplituda=round(A, 4), rola="drobna"))
    rr = np.hypot(x, y - 1.6)
    h += 0.035 * c["impuls_ataku"] * np.sin(22 * rr - 6 * t) * np.exp(-1.4 * rr)
    h += 0.003 * np.sin(13 * x + 7 * y) * np.sin(5 * y - 3 * x)
    hn = (h - h.min()) / (np.ptp(h) + 1e-9)
    turkus, perla = rgb("#1FB8B5"), rgb("#EEF1F2")
    w = (0.35 + 0.65 * hn ** 1.5)[:, None]
    col = (turkus * (1 - hn[:, None] ** 2) + perla * hn[:, None] ** 2) * w
    em = splat(np.stack([x, y, h], 1), col * 0.022, kam)
    tlo = tlo_gradient(rgb("#040A1C"), rgb("#08142E"), swiatlo=(0.5, 0.42, 0.35, rgb("#0B2238")))
    return kompozycja(tlo, em, 1.1, 0.4), dict(fale=fale, impuls_kregu=round(c["impuls_ataku"], 3))


# ----------------------------------------------------------------------------- 3. fraktalny ogród
def preset_ogrod(c, t, rng):
    """Samopodobne rozgałęzienia z drobin. Złożoność ← gęstość ataków (ozdobniki, rozwój frazy) + wysokie
    pasmo + energia; liczba odnóg z węzła 2–3 ← liczba jednocześnie brzmiących klas dźwięków;
    kąt rozwarcia ← centroid widmowy. Kwiaty (miedź) ∝ wysokie pasmo."""
    kam = Kamera((0, -2.6, 1.05), (0, 1.3, 0.95))
    zl = float(np.clip(0.35 * c["energia"] + 0.35 * min(1, c["gestosc_atakow"] / 4) + 0.30 * c["wysokie"], 0, 1))
    glebia = 2 + int(round(6 * zl))
    odnogi = 3 if c["wielodzwiek"] >= 4 else 2
    kat = math.radians(float(np.clip(16 + 16 * (c["centroid_hz"] - 400) / 1800, 14, 34)))
    rosliny = [(-1.15, 1.6, 0.85), (0.05, 2.3, 1.0), (1.2, 1.25, 0.8)]
    liczba = 1 if zl < 0.2 else (2 if zl < 0.45 else 3)
    Ps, Cs = [], []
    fiolet, lawenda, miedz = rgb("#6A3FC0"), rgb("#C9B6F0"), rgb("#D9944A")
    gal = 0

    def rosnij(p, d, L, poz, ziarno):
        nonlocal gal
        q = p + d * L
        n = max(30, int(L * 9000))
        s = ziarno.random(n)[:, None]
        grub = 0.012 * (0.72 ** poz)
        pts = p + (q - p) * s + ziarno.normal(0, grub, (n, 3))
        u = poz / max(glebia, 1)
        Ps.append(pts); Cs.append(np.tile((fiolet * (1 - u) + lawenda * u) * 0.05, (n, 1)))
        gal += 1
        if poz >= glebia:
            m = int(250 + 1600 * c["wysokie"])
            Ps.append(q + ziarno.normal(0, 0.03, (m, 3))); Cs.append(np.tile(miedz * 0.06, (m, 1)))
            return
        oś = np.cross(d, [0.0, 1.0, 0.0]); oś = oś / (np.linalg.norm(oś) + 1e-9)
        for j in range(odnogi):
            phi = 2 * math.pi * j / odnogi + 0.9 * poz
            obr = math.cos(phi) * oś + math.sin(phi) * np.cross(d, oś)
            nd = d * math.cos(kat) + obr * math.sin(kat) + ziarno.normal(0, 0.05, 3)
            nd /= np.linalg.norm(nd)
            rosnij(q, nd, L * 0.74, poz + 1, ziarno)

    for i, (px, py, sk) in enumerate(rosliny[:liczba]):
        rosnij(np.array([px, py, 0.0]), np.array([0, 0, 1.0]), 0.42 * sk, 0, np.random.default_rng(rng.integers(1 << 30) + i))
    # mgiełka gruntu
    Ng = 60_000
    Ps.append(np.stack([rng.normal(0, 1.4, Ng), 0.6 + rng.random(Ng) * 3, np.abs(rng.normal(0, 0.01, Ng))], 1))
    Cs.append(np.tile(lawenda * 0.008, (Ng, 1)))
    em = splat(np.vstack(Ps), np.vstack(Cs), kam)
    tlo = tlo_gradient(rgb("#0E0718"), rgb("#1A0E24"), swiatlo=(0.5, 0.35, 0.4, rgb("#1E1030")))
    return kompozycja(tlo, em, 1.2, 0.35), dict(zlozonosc=round(zl, 3), glebia=glebia, odnogi=odnogi,
                                                 kat_stopnie=round(math.degrees(kat), 1), rosliny=liczba, galezie=gal)


# ----------------------------------------------------------------------------- 4. orbity rezonansu
def preset_orbity(c, t, rng):
    """Krzywe Lissajous z par najsilniejszych szczytów widma: stosunek częstotliwości f_j/f_i przybliżony
    małym ułamkiem p/q (mianownik ≤ 9). To interpretacja: w muzyce wielogłosowej szczyty są mieszaniną
    dźwięków i alikwotów, a nie jedną idealną parą sinusoid. Cisza → jeden słaby okrąg (1:1)."""
    kam = Kamera((0.35, -3.1, 0.75), (0, 0, 0.05))
    sz = [s for s in c["szczyty"] if s[1] > 0.10][:4]
    pary = []
    for i in range(len(sz)):
        for j in range(i + 1, len(sz)):
            fi, fj = sorted([sz[i][0], sz[j][0]])
            fr = Fraction(fj / fi).limit_denominator(9)
            blad = abs(float(fr) - fj / fi) / (fj / fi)
            pary.append(dict(f1=round(fi, 1), f2=round(fj, 1), p=fr.numerator, q=fr.denominator,
                             blad_proc=round(100 * blad, 2), sila=round(sz[i][1] * sz[j][1], 3)))
    pary = sorted(pary, key=lambda d: -d["sila"])[:4]
    if c["energia"] < 0.03 or not pary:
        pary = [dict(f1=None, f2=None, p=1, q=1, blad_proc=0.0, sila=0.15)]
    kolory = [rgb("#D8DDE6"), rgb("#8FCBFF"), rgb("#FFB347"), rgb("#BFE6FF")]
    Ps, Cs = [], []
    for k, pr in enumerate(pary):
        p, q = pr["p"], pr["q"]
        if p > 12 or q > 12:
            g = math.gcd(p, q); p, q = max(1, p // g), max(1, q // g)
        M = int(60_000 + 260_000 * pr["sila"] * (0.4 + c["energia"]))
        tau = rng.random(M) * 2 * math.pi
        R = 0.95 - 0.13 * k
        d = math.pi / 2 + 0.4 * k + 0.25 * t
        x = R * np.sin(p * tau + d); y = R * np.sin(q * tau); z = 0.38 * R * np.sin((p + q) * tau / 2 + k)
        a = math.radians(28 * k)
        X = x * math.cos(a) - y * math.sin(a) * 0.35; Y = x * math.sin(a) * 0.35 + y * 0.35 * math.cos(a) + z * 0.2
        Z = y * 0.9 + z * 0.3
        P = np.stack([X, Y, Z], 1) + rng.normal(0, 0.004 + 0.01 * c["impuls_ataku"], (M, 3))
        Ps.append(P); Cs.append(np.tile(kolory[k % 4] * 0.05 * (0.5 + c["energia"]), (M, 1)))
        pr["p_uzyte"], pr["q_uzyte"] = p, q
    em = splat(np.vstack(Ps), np.vstack(Cs), kam, glebia=0.35)
    tlo = tlo_gradient(rgb("#05070B"), rgb("#0B0F18"), swiatlo=(0.5, 0.5, 0.3, rgb("#0E141E")))
    return kompozycja(tlo, em, 1.15, 0.45), dict(krzywe=pary)


# ----------------------------------------------------------------------------- 5. topografia dźwięku
def _gradient(stopy, u):
    """Interpolacja liniowa koloru po liście stopów (równo rozłożonych na 0..1)."""
    s = np.array([rgb(k) for k in stopy], np.float32)
    x = np.clip(u, 0, 1) * (len(s) - 1)
    i = np.minimum(x.astype(np.int64), len(s) - 2)
    f = (x - i)[:, None]
    return s[i] * (1 - f) + s[i + 1] * f


# Paleta „tory i kulki” (inspiracje/styl_tory_kulki.jpg): granat → kobalt → turkus → róż → pomarańcz → żółć
PALETA_TORY = ["#2A5FD0", "#2FC2C4", "#F02E9A", "#F7963A", "#F9DC4A"]


def preset_topografia_tory(c, t, rng, analiza=None):
    """Topografia dźwięku w kolorach „tory i kulki”. Ten sam teren co preset 5; kolor warstwic ← wysokość
    terenu (doliny granatowe, grzbiety różowo-żółte), przesunięcie palety ← centroid (jaśniejsza barwa
    dźwięku → cieplejsze grzbiety), wiry po atakach podświetlone różem, warstwice jak żółte/białe tory."""
    return preset_topografia(c, t, rng, analiza, styl="tory")


def preset_topografia(c, t, rng, analiza=None, styl="noc"):
    """Krajobraz z piasku: niskie pasmo → duże wydmy, średnie → średnie fale, wysokie → drobne grzbiety;
    ostatnie ataki (≤ 4 s) → lokalne wiry (pozycja x ← wysokość szczytu w chwili ataku, y ← jak dawno);
    kontury co stałą wysokość. Cisza → prawie płaska równina."""
    kam = Kamera((0, -0.85, 1.25), (0, 2.6, 0))
    N = 1_700_000
    x = (rng.random(N) * 2 - 1) * (0.6 + 2.4 * rng.random(N) ** 0.5)
    y = 0.25 + 5.0 * rng.random(N) ** 1.5
    duzy, sredni, drobny = szum(rng, 2.2), szum(rng, 7.0), szum(rng, 26.0)
    wiry = []
    if analiza is not None:
        for ta in analiza.ataki[(analiza.ataki <= t) & (analiza.ataki > t - 4.0)]:
            sz = analiza.szczyty(float(ta), n=1)
            if sz:
                f = sz[0][0]
                wiry.append((float(np.clip((math.log2(f / 220) / 3) * 2.6 - 1.3, -1.8, 1.8)), 1.0 + (t - ta) * 0.9,
                             float(math.exp(-(t - ta) / 2.0))))

    def wys(x, y):
        xx, yy = x.copy(), y.copy()
        for wx, wy, s in wiry:   # zawirowanie współrzędnych
            dx, dy = xx - wx, yy - wy
            r2 = dx * dx + dy * dy
            a = 2.2 * s * np.exp(-r2 / 0.08)
            ca, sa = np.cos(a), np.sin(a)
            xx, yy = wx + dx * ca - dy * sa, wy + dx * sa + dy * ca
        h = 0.004 * drobny(xx + 3, yy)
        h += 0.30 * c["niskie"] * duzy(xx, yy)
        h += 0.07 * c["srednie"] * sredni(xx + 7, yy + 1)
        h += 0.03 * c["wysokie"] * (1 - np.abs(drobny(xx, yy + 5)))
        for wx, wy, s in wiry:
            h -= 0.05 * s * np.exp(-((x - wx) ** 2 + (y - wy) ** 2) / 0.05)
        return h
    e = 0.01
    h = wys(x, y)
    hx = (wys(x + e, y) - h) / e; hy = (wys(x, y + e) - h) / e
    n = np.stack([-hx, -hy, np.ones_like(h)], 1); n /= np.linalg.norm(n, axis=1, keepdims=True)
    L = np.array([-0.55, 0.35, 0.45]); L /= np.linalg.norm(L)
    sw = np.clip(n @ L, 0, 1) ** 1.3
    kontur = (np.mod(h * 22, 1.0) < 0.07).astype(np.float32)
    if styl == "tory":
        # wysokość względna (odporna na skalę: percentyle), przesunięcie ku ciepłym barwom ← centroid
        lo, hi = np.percentile(h, [3, 97])
        u = (h - lo) / (hi - lo + 1e-9)
        cieplo = float(np.clip((c["centroid_hz"] - 300) / 1500, 0, 1)) * 0.15
        baza = _gradient(PALETA_TORY, np.clip(u, 0, 1) ** 0.6 * 0.88 + cieplo)
        col = baza * (0.45 + 0.55 * sw[:, None])
        # warstwice = tory: żółte na stokach, białe na grzbietach
        tor = rgb("#F9DC4A") * (1 - u[:, None]) + rgb("#FFF6E8") * u[:, None]
        col = col * (1 - 0.55 * kontur[:, None]) + tor * (0.55 * kontur[:, None])
        # wiry po atakach: różowa poświata w ich okolicy
        if wiry:
            blask = np.zeros_like(h)
            for wx, wy, s in wiry:
                blask += s * np.exp(-((x - wx) ** 2 + (y - wy) ** 2) / 0.12)
            b = np.clip(blask, 0, 1)[:, None] * 0.6
            col = col * (1 - b) + rgb("#FF3FA8") * b
        em = splat(np.stack([x, y, h], 1), col * 0.12, kam, glebia=0.4)
        tlo = tlo_gradient(rgb("#040A1E"), rgb("#08173A"), winieta=0.4, swiatlo=(0.5, 0.42, 0.3, rgb("#0A1F4C")))
        return kompozycja(tlo, em, 1.2, 0.35), dict(skala_wydm=round(0.30 * c["niskie"], 4), skala_fal=round(0.07 * c["srednie"], 4),
                                                     skala_grzbietow=round(0.03 * c["wysokie"], 4), wiry=len(wiry),
                                                     paleta="tory", przesuniecie_ciepla=round(cieplo, 3))
    kosc, roz, cien = rgb("#F3EADA"), rgb("#E0A190"), rgb("#101A3A")
    mix = np.clip(0.5 + 6 * h, 0, 1)[:, None]
    jasne = kosc * mix + roz * (1 - mix)
    col = cien * (1 - sw[:, None]) * 0.9 + jasne * sw[:, None]
    col = col * (0.75 + 0.6 * kontur[:, None])
    # wzmocnienie 0.085 (było 0.018) i jaśniejsze stoki w cieniu: przy 1,7 mln drobin rozłożonych na całą
    # równinę krajobraz ginął w tle (p99 jasności 27 wobec 57–164 w pozostałych presetach)
    em = splat(np.stack([x, y, h], 1), col * 0.085, kam, glebia=0.4)
    tlo = tlo_gradient(rgb("#050816"), rgb("#0A1028"))
    return kompozycja(tlo, em, 1.25, 0.30), dict(skala_wydm=round(0.30 * c["niskie"], 4), skala_fal=round(0.07 * c["srednie"], 4),
                                                  skala_grzbietow=round(0.03 * c["wysokie"], 4), wiry=len(wiry))


PRESETY = {
    "1_cymatyka_zloty_piasek": preset_cymatyka,
    "2_ocean_harmonicznych": preset_ocean,
    "3_fraktalny_ogrod": preset_ogrod,
    "4_orbity_rezonansu": preset_orbity,
    "5_topografia_dzwieku": preset_topografia,
    "5b_topografia_tory": preset_topografia_tory,
}
