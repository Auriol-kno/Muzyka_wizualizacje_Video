"""Koncepcje do drugiej wersji klipu: połączenie motywów z `zrodla/inspiracje/` (złote poziomice na
ciemnym terenie, rzeki iskier z bokeh, złota spirala z kryształami, kryształ w jedwabnym dymie).

Ta sama zasada co w `czasteczki.py`: każda liczba sterująca obrazem pochodzi z pomiaru nagrania
(`analiza.py`) i trafia do słownika `parametry`. Funkcje: f(c, t, rng, analiza) -> (obraz 0..1, parametry).
"""
import math

import cv2
import numpy as np

from wizualizacje.czasteczki import H, W, Kamera, kompozycja, rgb, splat, szum, tlo_gradient

PHI = (1 + 5 ** 0.5) / 2
ZLOTO, ZLOTO_JASNE = rgb("#F2B046"), rgb("#FFE3A3")


# ----------------------------------------------------------------------------- pomocnicze
def splat2d(x, y, col, sig=0.0):
    """Drobiny w pikselach ekranu → obraz emisji (interpolacja dwuliniowa, opcjonalne rozmycie)."""
    ok = (x >= 0) & (x < W - 1) & (y >= 0) & (y < H - 1)
    x, y, col = x[ok], y[ok], col[ok]
    x0 = np.floor(x).astype(np.int64); y0 = np.floor(y).astype(np.int64)
    fx = (x - x0).astype(np.float32); fy = (y - y0).astype(np.float32)
    acc = np.zeros((3, H * W), np.float64)
    for dx, dy, w in ((0, 0, (1 - fx) * (1 - fy)), (1, 0, fx * (1 - fy)), (0, 1, (1 - fx) * fy), (1, 1, fx * fy)):
        idx = (y0 + dy) * W + (x0 + dx)
        for ch in range(3):
            acc[ch] += np.bincount(idx, weights=col[:, ch] * w, minlength=H * W)
    out = acc.reshape(3, H, W).transpose(1, 2, 0).astype(np.float32)
    return cv2.GaussianBlur(out, (0, 0), sig) if sig > 0.3 else out


def ostatnie_ataki(analiza, t, okno, maks=12):
    """[(czas ataku, częstotliwość najsilniejszego szczytu, siła 0..1 z narastaniem 0,1 s)] – najnowsze."""
    if analiza is None:
        return []
    out = []
    for ta in analiza.ataki[(analiza.ataki <= t) & (analiza.ataki > t - okno)][-maks:]:
        sz = analiza.szczyty(float(ta), n=1)
        f = sz[0][0] if sz else 440.0
        r = min(1.0, (t - ta) / 0.1)
        out.append((float(ta), float(f), float(r * r * (3 - 2 * r) * analiza.atak[analiza.idx(float(ta))])))
    return out


def poz_tonu(f):
    """Wysokość dźwięku → pozycja −1..1 (A3 … A6)."""
    return float(np.clip(math.log2(max(f, 30) / 220) / 3 * 2 - 1, -1, 1))


def spirala_zlota(x0, y0, wys, kroki=10, na_luk=90):
    """Prostokąt złoty (szer = wys·φ) dzielony na kwadraty. Zwraca listę kwadratów i punkty spirali
    (od zewnątrz do środka) – łuki ćwiartek okręgu, ciągłe między kwadratami."""
    rx, ry, rw, rh = x0, y0, wys * PHI, wys
    kwadraty, pkt = [], []
    for k in range(kroki):
        d = k % 4
        if d == 0:
            s = rh; kw = (rx, ry, s); c, a0 = (rx + s, ry + s), 180; rx += s; rw -= s
        elif d == 1:
            s = rw; kw = (rx, ry, s); c, a0 = (rx, ry + s), 270; ry += s; rh -= s
        elif d == 2:
            s = rh; kw = (rx + rw - s, ry, s); c, a0 = (rx + rw - s, ry), 0; rw -= s
        else:
            s = rw; kw = (rx, ry + rh - s, s); c, a0 = (rx + s, ry + rh - s), 90; rh -= s
        kwadraty.append(kw)
        a = np.radians(a0 + np.linspace(0, 90, na_luk))
        pkt.append(np.stack([c[0] + s * np.cos(a), c[1] + s * np.sin(a)], 1))
    return kwadraty, np.concatenate(pkt)


def linie(img, punkty, kolor, grubosc=1):
    """Antyaliasowana łamana na obrazie float (rysowana w 4× podpikselach)."""
    p = np.round(np.asarray(punkty) * 4).astype(np.int32).reshape(-1, 1, 2)
    cv2.polylines(img, [p], False, tuple(float(v) for v in kolor), grubosc, cv2.LINE_AA, shift=2)


# ----------------------------------------------------------------------------- A. złote poziomice
_LINIE = {}


def _teren_liniowy(rng, e=0.01):
    """Teren z ~1,3 mln drobin ułożonych w poziome linie (jak warstwice na inspiracji). Pola szumu
    liczone raz na seed dla (x,y), (x+e,y), (x,y+e)."""
    klucz = str(rng.bit_generator.state["state"])
    if klucz not in _LINIE:
        ny, nx = 190, 6500
        yr = 0.35 + 7.5 * (np.arange(ny) / (ny - 1)) ** 1.5
        u = np.linspace(-1, 1, nx)
        x = (u[None, :] * (1.2 + 0.95 * yr[:, None])).ravel().astype(np.float32)
        y = np.repeat(yr, nx).astype(np.float32)
        x += (rng.random(x.size).astype(np.float32) - 0.5) * 0.002          # bez moiré
        duzy, sredni, drobny = szum(rng, 0.9), szum(rng, 2.6), szum(rng, 9.0)
        pola = []
        for ox, oy in ((0, 0), (e, 0), (0, e)):
            px, py = x + ox, y + oy
            d = duzy(px, py)
            # góry: gładkie wzniesienia + łagodny grzbiet (bez ostrych zagięć)
            gory = 0.55 * d + 0.45 * np.clip(1 - np.abs(d) * 0.8, 0, 1) ** 3
            pola.append(np.stack([gory, sredni(px + 5, py), drobny(px, py + 3)], 1).astype(np.float32))
        _LINIE.clear()
        _LINIE[klucz] = (x, y, pola, e)
    return _LINIE[klucz]


def _poziomice(c, t, rng, analiza):
    x, y, pola, e = _teren_liniowy(rng)
    dal = np.clip((y - 0.5) / 3.5, 0, 1)
    wagi = np.array([0.08 + 0.30 * c["niskie"], 0.012 + 0.03 * c["srednie"], 0.002 + 0.004 * c["wysokie"]], np.float32)
    kregi = [(poz_tonu(f) * 1.6, 1.3 + 0.35 * (t - ta), t - ta, s) for ta, f, s in ostatnie_ataki(analiza, t, 3.0, 8)]

    def wys(k, ox, oy):
        p = pola[k]
        h = (p[:, 0] * wagi[0]) * (0.35 + 0.65 * dal) + p[:, 1] * wagi[1] + p[:, 2] * wagi[2]
        for wx, wy, wiek, s in kregi:          # nuta → koncentryczne kręgi na terenie (jak słoje na inspiracji)
            dx, dy = x + ox - wx, y + oy - wy
            m = np.flatnonzero(dx * dx + dy * dy < 1.0)
            r = np.sqrt(dx[m] ** 2 + dy[m] ** 2)
            front = np.exp(-((r - 0.25 - wiek * 0.35) / 0.25) ** 2)
            h[m] += 0.018 * s * np.cos(r * 38 - wiek * 7) * front * math.exp(-wiek / 1.5)
        return h
    h = wys(0, 0, 0)
    hx = (wys(1, e, 0) - h) / e; hy = (wys(2, 0, e) - h) / e
    n = np.stack([-hx, -hy, np.ones_like(h)], 1); n /= np.linalg.norm(n, axis=1, keepdims=True)
    L = np.array([0.45, 0.75, 0.48]); L /= np.linalg.norm(L)                 # światło zza grzbietów
    sw = np.clip(n @ L, 0, 1)
    baza = rgb("#26344A") * (1 - sw[:, None]) + rgb("#8696B0") * sw[:, None]
    lo, hi = np.percentile(h, [5, 99])
    wzg = np.clip((h - lo) / (hi - lo + 1e-6), 0, 1)                       # wysokość względna
    zl = (np.clip((sw - 0.4) / 0.4, 0, 1) ** 1.2 * wzg ** 1.2) * (0.35 + 1.2 * c["energia"])
    col = baza * 0.75 + (ZLOTO * (1 - zl[:, None] * 0.3) + ZLOTO_JASNE * zl[:, None] * 0.3) * zl[:, None] * 3.5
    kam = Kamera((0, -0.7, 1.05), (0, 3.8, 0.0))
    em = splat(np.stack([x, y, h], 1), col * 0.09, kam, glebia=0.3)
    # złoty pył nad terenem: unosi się powoli, rozbłyskuje po atakach
    M = 2600
    r2 = np.random.default_rng(7)
    px = (r2.random(M) * 2 - 1) * 3.2; py = 0.6 + 6 * r2.random(M)
    pz = 0.15 + np.mod(r2.random(M) * 1.4 + 0.025 * t, 1.4)
    blysk = 0.35 + 1.6 * c["impuls_ataku"] * (r2.random(M) < 0.35)
    em += splat(np.stack([px, py, pz], 1), ZLOTO[None, :] * (blysk * 0.5)[:, None], kam, glebia=1.1)
    tlo = tlo_gradient(rgb("#04060B"), rgb("#0A0F18"), winieta=0.5, swiatlo=(0.5, 0.3, 0.45, rgb("#152033")))
    par = dict(wydmy=round(float(wagi[0]), 4), fale=round(float(wagi[1]), 4), kregi_nut=len(kregi),
               zloto=round(0.25 + 1.1 * c["energia"], 3))
    return tlo, em, par


def koncepcja_poziomice(c, t, rng, analiza=None):
    """A. Złote poziomice: ciemny teren z gęstych linii, grzbiety podświetlone złotem (← głośność),
    każda nuta zostawia na terenie koncentryczne kręgi (pozycja ← wysokość dźwięku), złoty pył."""
    tlo, em, par = _poziomice(c, t, rng, analiza)
    return kompozycja(tlo, em, 1.15, 0.4), par


# ----------------------------------------------------------------------------- B. rzeka iskier
def _rzeka(c, t, N=520_000, seed=11):
    r = np.random.default_rng(seed)
    zgiecie = float(np.clip((c["centroid_hz"] - 300) / 1500, 0, 1))

    def os_rzeki(y):
        return ((0.5 + 0.9 * zgiecie) * np.sin(0.42 * y + 0.2 + 0.3 * math.sin(t * 0.21)) - 0.1,
                -0.45 + 0.1 * np.sin(0.7 * y + t * 0.3))
    s0 = r.random(N); poprz = r.standard_normal(N) * (0.35 + 0.8 * r.random(N)); pion = r.standard_normal(N) * 0.04
    s = np.mod(s0 + t * 0.010, 1.0)
    y = 0.15 + 10.0 * s ** 1.6
    xc, zc = os_rzeki(y)
    szer = (0.18 + 0.4 * c["energia"]) * (0.35 + 0.12 * y)
    x = xc + poprz * szer
    z = zc + pion + 0.08 * poprz * szer
    u = r.random(N)
    p_zl = 0.18 + 0.35 * c["wysokie"]
    kol = np.where(u[:, None] < p_zl, ZLOTO[None, :] * 1.2,
                   np.where(u[:, None] < p_zl + 0.2, rgb("#3FD8E8")[None, :],
                            np.where(u[:, None] < p_zl + 0.55, rgb("#7FB8FF")[None, :], rgb("#E8F2FF")[None, :])))
    w = r.lognormal(0, 1.25, N) * (0.35 + 0.9 * c["energia"])
    w *= 1 + 4 * c["impuls_ataku"] * (r.random(N) < 0.05)
    # świetlista nić przez środek rzeki
    nn = 80_000
    yn = 0.15 + 10.0 * np.linspace(0, 1, nn) ** 1.6
    xn, zn = os_rzeki(yn)
    xn = xn + 0.03 * np.sin(yn * 3)
    # bokeh: rzadkie, jasne drobiny tuż przed kamerą (rozmyte przez głębię ostrości)
    nb = 2500
    sb = r.random(nb) ** 2
    yb = 0.05 + 1.6 * sb
    xb, zb = os_rzeki(yb)
    xb = xb + r.standard_normal(nb) * 0.35; zb = zb + r.standard_normal(nb) * 0.12
    kb = np.where(r.random(nb)[:, None] < p_zl + 0.1, ZLOTO[None, :], rgb("#9FD4FF")[None, :])
    wb = (0.5 + 2.5 * r.random(nb) ** 2) * (0.4 + 0.8 * c["energia"])
    P = np.concatenate([np.stack([x, y, z], 1), np.stack([xn, yn, zn], 1), np.stack([xb, yb, zb], 1)])
    C = np.concatenate([kol * w[:, None], np.repeat(rgb("#CFEAFF")[None, :], nn, 0) * (0.35 + 0.6 * c["srednie"]),
                        kb * wb[:, None] * 25])
    return P, C, dict(zgiecie=round(zgiecie, 3), szerokosc=round(0.18 + 0.4 * c["energia"], 3),
                      udzial_zlota=round(p_zl, 3))


def koncepcja_rzeka(c, t, rng, analiza=None):
    """B. Rzeka iskier: wstęga drobin płynie w głąb kadru; szerokość ← głośność, zakręt ← barwa
    (centroid), udział złotych iskier ← wysokie tony, ataki rozbłyskują pojedyncze iskry. Głęboki bokeh."""
    P, C, par = _rzeka(c, t)
    kam = Kamera((0.1, -0.4, 0.05), (0.2, 3.2, -0.45))
    em = splat(P, C * 0.06, kam, glebia=1.1, warstwy=5)
    tlo = tlo_gradient(rgb("#03060E"), rgb("#07101F"), winieta=0.5, swiatlo=(0.72, 0.42, 0.35, rgb("#1A2A46")))
    return kompozycja(tlo, em, 1.1, 0.5), par


# ----------------------------------------------------------------------------- C. złota spirala
_MARMUR = {}


def tlo_marmur(seed=3, gora="#050C22", dol="#1A3263"):
    """Granatowy „marmur kosmiczny”: szum wielooktawowy + żyłki + złote drobinki (statyczne)."""
    if seed not in _MARMUR:
        r = np.random.default_rng(seed)
        yy, xx = np.mgrid[0:H // 4, 0:W // 4].astype(np.float32) / (H // 4)
        v = sum(szum(r, sk)(xx, yy) / (i + 1) for i, sk in enumerate((3.0, 7.0, 16.0, 40.0)))
        v = (v - v.min()) / (v.max() - v.min())
        zylki = np.exp(-(np.abs(szum(r, 9.0)(xx + 2, yy)) / 0.05) ** 2) * 0.35
        m = np.clip(v ** 1.6 + zylki, 0, 1)[..., None]
        img = rgb(gora) * (1 - m) + rgb(dol) * m
        img = cv2.resize(img.astype(np.float32), (W, H), interpolation=cv2.INTER_CUBIC)
        k = r.random(5000)
        gx, gy = (r.random(5000) * W).astype(int), (r.random(5000) * H).astype(int)
        img[gy, gx] += ZLOTO * (0.15 + 0.5 * k[:, None] ** 3)
        _MARMUR[seed] = img * (1 - 0.35 * np.clip(((np.mgrid[0:H, 0:W][1] - W / 2) / (W / 2)) ** 2, 0, 1))[..., None]
    return _MARMUR[seed].copy()


def _szkla(img, t, c, seed=5, ile=7, cx=W * 0.5, cy=H * 0.5, rozrzut=0.32):
    """Przezroczyste odłamki szkła: jaśniejsze wypełnienie + cienkie krawędzie; obrót ← czas i bas."""
    r = np.random.default_rng(seed)
    em = np.zeros_like(img)
    for k in range(ile):
        n = 3 + (k % 2)
        sx, sy = cx + (r.random() - 0.5) * W * rozrzut * 1.6, cy + (r.random() - 0.5) * H * rozrzut * 1.6
        R = H * (0.12 + 0.2 * r.random())
        a0 = r.random() * 6.28 + (0.03 + 0.04 * r.random()) * t * (1 if k % 2 else -1) + 0.25 * c["niskie"]
        ang = a0 + np.sort(r.random(n)) * 6.28
        rad = R * (0.6 + 0.6 * r.random(n))
        pts = np.stack([sx + rad * np.cos(ang), sy + rad * np.sin(ang) * 0.8], 1)
        maska = np.zeros((H, W), np.float32)
        cv2.fillPoly(maska, [np.round(pts * 4).astype(np.int32)], 1.0, cv2.LINE_AA, shift=2)
        img += maska[..., None] * rgb("#9FB6D8") * 0.07
        linie(em, np.vstack([pts, pts[:1]]), rgb("#DCE8FF") * 0.18)
    return em


def koncepcja_spirala(c, t, rng, analiza=None):
    """C. Złota spirala: prostokąt złoty i spirala Fibonacciego na granatowym marmurze, odłamki szkła,
    smuga mgławicy (jasność ← głośność). Każda nuta wpada w spiralę jako świetlny punkt, który w 4 s
    przebiega od zewnątrz do środka – matematyka utworu widoczna wprost (φ ≈ 1,618)."""
    tlo = tlo_marmur()
    em = _szkla(tlo, t, c)
    wys = H * 0.62
    x0, y0 = W / 2 - wys * PHI / 2, H / 2 - wys / 2
    kw, sp = spirala_zlota(x0, y0, wys, kroki=10)
    siatka = np.zeros_like(tlo)
    for (qx, qy, s) in kw:
        linie(siatka, [(qx, qy), (qx + s, qy), (qx + s, qy + s), (qx, qy + s), (qx, qy)], ZLOTO * 0.28)
    linie(siatka, sp, ZLOTO * (0.55 + 0.6 * c["energia"]), 2)
    em += siatka
    # nuty biegnące po spirali
    ataki = ostatnie_ataki(analiza, t, 4.0, 14)
    if ataki:
        idx = np.array([min(len(sp) - 1, int((t - ta) / 4.0 * len(sp))) for ta, f, s in ataki])
        sila = np.array([s for _, _, s in ataki]) * np.exp(-np.array([t - ta for ta, _, _ in ataki]) / 3)
        # świetlny punkt + krótki ogon za nim
        ogon = np.concatenate([np.clip(idx - k * 4, 0, None) for k in range(12)])
        jas = np.concatenate([(0.3 + sila) * 700 * math.exp(-k / 4) for k in range(12)])
        em += splat2d(sp[ogon, 0], sp[ogon, 1], ZLOTO_JASNE[None, :] * jas[:, None], sig=7)
    # mgławica: smuga z prawego górnego rogu ku dołowi
    r = np.random.default_rng(21)
    N = 220_000
    s = r.random(N)
    ax, ay, bx, by = W * 0.78, -H * 0.05, W * 0.52, H * 1.05
    fala = np.sin(s * 5 + t * 0.15) * 60
    szer = (30 + 120 * c["energia"]) * (0.6 + r.standard_normal(N) * 0.7)
    nx_, ny_ = (by - ay), -(bx - ax); dl = math.hypot(nx_, ny_); nx_ /= dl; ny_ /= dl
    px = ax + (bx - ax) * s + nx_ * (szer + fala); py = ay + (by - ay) * s + ny_ * (szer + fala)
    u = r.random(N)
    kol = np.where(u[:, None] < 0.35, ZLOTO[None, :], np.where(u[:, None] < 0.75, rgb("#6FB4FF")[None, :], rgb("#E6F0FF")[None, :]))
    w = r.lognormal(0, 1.0, N) * (0.03 + 0.07 * c["energia"])
    neb = splat2d(px, py, kol * w[:, None], sig=0.8)
    em += neb + 0.6 * cv2.GaussianBlur(neb, (0, 0), 12)
    return kompozycja(tlo, em, 1.0, 0.35), dict(phi=round(PHI, 4), nuty_na_spirali=len(ataki),
                                                 jasnosc_spirali=round(0.55 + 0.6 * c["energia"], 3))


# ----------------------------------------------------------------------------- D. kryształ w jedwabiu
def _dwudziestoscian():
    v = []
    for a in (-1, 1):
        for b in (-PHI, PHI):
            v += [(0, a, b), (a, b, 0), (b, 0, a)]
    v = np.array(v, float) / math.hypot(1, PHI)
    d = np.linalg.norm(v[:, None] - v[None], axis=2)
    kr = d[d > 1e-6].min()
    kraw = [(i, j) for i in range(12) for j in range(i + 1, 12) if abs(d[i, j] - kr) < 1e-6]
    sc = [(i, j, k) for i, j in kraw for k in range(j + 1, 12) if abs(d[i, k] - kr) < 1e-6 and abs(d[j, k] - kr) < 1e-6]
    return v, kraw, sc


def koncepcja_krysztal(c, t, rng, analiza=None):
    """D. Kryształ w jedwabiu: obracający się dwudziestościan (złote krawędzie, ciemne szkło), światło
    w środku ← głośność, jedwabne pasma dymu (falowanie ← średnie pasmo), złote iskry wylatują
    z kryształu po każdym ataku (kierunek ← wysokość dźwięku)."""
    tlo = tlo_gradient(rgb("#081129"), rgb("#101C3C"), winieta=0.45)
    em = np.zeros_like(tlo)
    cx, cy = W * 0.47, H * 0.5
    # jedwab: dwie wiązki krzywych omijających kryształ
    jedw = np.zeros_like(tlo)
    xs = np.linspace(-0.1 * W, 1.1 * W, 700)
    for k in range(70):
        wiaz = 1 if k % 2 else -1
        y0 = cy + wiaz * (H * 0.2 + k * 3.2)
        faza = k * 0.37 + t * 0.12
        amp = (25 + 80 * c["srednie"]) * (0.5 + 0.5 * math.sin(k * 0.7))
        ys = y0 + amp * np.sin(xs / W * 5 + faza) + 50 * np.sin(xs / W * 2.1 - faza * 0.6) - wiaz * (xs - cx) * 0.35
        odp = np.exp(-((xs - cx) / (W * 0.18)) ** 2) * H * 0.18 * wiaz     # omija kryształ
        linie(jedw, np.stack([xs, ys + odp], 1), rgb("#B9C8E2") * 0.22)
    em += cv2.GaussianBlur(jedw, (0, 0), 1.2) + 0.8 * cv2.GaussianBlur(jedw, (0, 0), 9)
    # kryształ
    v, kraw, sc = _dwudziestoscian()
    a, b = 0.11 * t, 0.07 * t + 0.4
    Rz = np.array([[math.cos(a), -math.sin(a), 0], [math.sin(a), math.cos(a), 0], [0, 0, 1]])
    Rx = np.array([[1, 0, 0], [0, math.cos(b), -math.sin(b)], [0, math.sin(b), math.cos(b)]])
    p = v @ (Rx @ Rz).T
    S = H * 0.27 * (1 + 0.05 * c["energia"])
    px, py = cx + S * p[:, 0] / (1 + 0.18 * p[:, 2]), cy - S * p[:, 1] / (1 + 0.18 * p[:, 2])
    szklo = np.zeros((H, W), np.float32)
    for i, j, k in sc:
        cv2.fillPoly(szklo, [np.round(np.array([[px[i], py[i]], [px[j], py[j]], [px[k], py[k]]]) * 4).astype(np.int32)],
                     1.0, cv2.LINE_AA, shift=2)
    tlo *= (1 - 0.55 * szklo[..., None])
    for i, j in kraw:
        tyl = (p[i, 2] + p[j, 2]) / 2 > 0
        linie(em, [(px[i], py[i]), (px[j], py[j])], ZLOTO * (0.25 if tyl else 0.75), 1 if tyl else 2)
    blask = 0.15 + 0.9 * c["energia"] + 0.5 * c["impuls_ataku"]
    yy, xx = np.mgrid[0:H, 0:W].astype(np.float32)
    em += (np.exp(-(((xx - cx - S * 0.25) ** 2 + (yy - cy + S * 0.1) ** 2) / (S * 0.28) ** 2)) * blask)[..., None] * ZLOTO_JASNE * 0.9
    # iskry po atakach
    P, Cw = [], []
    for ta, f, s in ostatnie_ataki(analiza, t, 3.0, 10):
        r = np.random.default_rng(int(ta * 1000))
        n = 400
        kier = 0.6 - poz_tonu(f) * 0.9 + r.standard_normal(n) * 0.5          # wyżej → bardziej w górę
        v_ = (0.3 + r.random(n)) * W * 0.32
        d = (t - ta) ** 0.6
        P.append(np.stack([cx + S * 0.25 + np.cos(kier) * v_ * d, cy - np.sin(kier) * v_ * d], 1))
        Cw.append(np.full(n, s * math.exp(-(t - ta) / 1.1) * 9) * (0.3 + r.random(n)))
    r = np.random.default_rng(8)
    pyl = np.stack([r.random(1800) * W, r.random(1800) * H], 1)
    P.append(pyl); Cw.append(0.6 + 2.5 * r.random(1800) ** 4)
    P = np.concatenate(P); Cw = np.concatenate(Cw)
    isk = splat2d(P[:, 0], P[:, 1], ZLOTO_JASNE[None, :] * Cw[:, None], sig=1.2)
    em += isk + cv2.GaussianBlur(isk, (0, 0), 4)
    return kompozycja(tlo, em, 1.0, 0.4), dict(blask=round(blask, 3), falowanie=round(25 + 80 * c["srednie"], 1),
                                                iskry=len(ostatnie_ataki(analiza, t, 3.0, 10)))


# ----------------------------------------------------------------------------- E. pejzaż nokturnu
def koncepcja_pejzaz(c, t, rng, analiza=None):
    """E. Pejzaż nokturnu (połączenie): złote poziomice na dole, na niebie rzeka iskier jak Droga
    Mleczna (jasność ← wysokie tony), w górze gwiazdozbiór spirali złotej, w który wpadają nuty."""
    tlo, em, par = _poziomice(c, t, rng, analiza)
    # Droga Mleczna: smuga drobin w poprzek nieba
    r = np.random.default_rng(31)
    N = 160_000
    s = r.random(N)
    px = s * W * 1.1 - W * 0.05
    os_ = H * 0.26 - (s - 0.5) * H * 0.22 + 18 * np.sin(s * 7 + t * 0.1)
    py = os_ + r.standard_normal(N) * (18 + 40 * r.random(N)) * (0.7 + 0.6 * c["wysokie"])
    u = r.random(N)
    kol = np.where(u[:, None] < 0.3, ZLOTO[None, :], np.where(u[:, None] < 0.7, rgb("#8FC8FF")[None, :], rgb("#E8F2FF")[None, :]))
    w = r.lognormal(0, 1.0, N) * (0.03 + 0.07 * c["wysokie"])
    niebo = splat2d(px, py, kol * w[:, None], sig=0.7)
    niebo = niebo + 0.7 * cv2.GaussianBlur(niebo, (0, 0), 14)
    # gwiazdozbiór spirali (lewy górny róg)
    wys = H * 0.26
    kw, sp = spirala_zlota(W * 0.06, H * 0.05, wys, kroki=8, na_luk=30)
    gw = sp[::6]
    jas = np.full(len(gw), 3.0)
    ataki = ostatnie_ataki(analiza, t, 4.0, 12)
    for ta, f, s_ in ataki:
        i = min(len(gw) - 1, int((t - ta) / 4.0 * len(gw)))
        jas[i] += 60 * s_
    niebo += splat2d(gw[:, 0], gw[:, 1], ZLOTO_JASNE[None, :] * jas[:, None], sig=2.0)
    linie(niebo, sp, ZLOTO * 0.18)
    # niebo tylko nad terenem: maska z jasności terenu (gdzie teren świeci, niebo przygaszone)
    tm = cv2.GaussianBlur(em.max(axis=2), (0, 0), 8)
    niebo *= np.clip(1 - tm / 0.05, 0.15, 1)[..., None]
    par.update(droga_mleczna=round(0.03 + 0.07 * c["wysokie"], 4), nuty_w_gwiazdozbiorze=len(ataki))
    return kompozycja(tlo, em + niebo, 1.15, 0.4), par


KONCEPCJE = {
    "A_zlote_poziomice": koncepcja_poziomice,
    "B_rzeka_iskier": koncepcja_rzeka,
    "C_zlota_spirala": koncepcja_spirala,
    "D_krysztal_w_jedwabiu": koncepcja_krysztal,
    "E_pejzaz_nokturnu": koncepcja_pejzaz,
}
