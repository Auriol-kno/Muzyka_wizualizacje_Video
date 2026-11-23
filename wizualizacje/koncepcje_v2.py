"""Koncepcje wersji 2 Nokturnu (`zrodla/inspiracje/2 wariacja`): złote poziomice na ciemnym terenie,
fala iskier z bokeh, góry z nici w mgle. Wszystkie sceny to obiekty 3D oglądane z kamery krążącej
wokół (parametr `azymut`), z 2–3 mln drobin, stałym światłem w świecie (główne + kontra), rozbłyskami
na nutach i delikatnymi gradientami (wysokość, głębia, mgła atmosferyczna).

Zasada jak w `czasteczki.py`: obraz wynika z pomiaru nagrania (`analiza.py`); słownik `parametry`
zawiera liczby, które go sterowały. Sygnatura: f(c, t, analiza, azymut) -> (obraz 0..1, parametry).
"""
import math

import cv2
import numpy as np
from scipy.special import jn_zeros, jv

from wizualizacje.czasteczki import H, W, Kamera, rgb, splat, szum
from wizualizacje.koncepcje import ostatnie_ataki

ZLOTO, ZLOTO_JASNE = rgb("#F2B046"), rgb("#FFE3A3")
LODOWY = rgb("#9CC4FF")


def _kier(v):
    v = np.array(v, float)
    return v / np.linalg.norm(v)


KLUCZ = _kier((-0.5, 0.35, 0.8))      # światło główne (księżyc, wysoko)
KONTRA = _kier((0.55, 0.75, 0.22))    # kontra nisko nad horyzontem – przy obrocie kamery raz za plecami, raz w kadrze


# ----------------------------------------------------------------------------- narzędzia
def gradient(stopy, u):
    S = np.array([rgb(s) for s in stopy], np.float32)
    u = np.clip(u, 0, 1) * (len(S) - 1)
    i = np.minimum(np.floor(u).astype(int), len(S) - 2)
    f = (u - i)[..., None].astype(np.float32)
    return S[i] * (1 - f) + S[i + 1] * f


def gladko(a, b, x):
    q = np.clip((x - a) / (b - a), 0, 1)
    return q * q * (3 - 2 * q)


def midi(f):
    return 12 * math.log2(max(f, 20) / 440) + 69


def kamera_orbita(azymut, promien=4.9, wys=1.85, cel=(0, 0, 0.12), ogniskowa=1.45):
    a = math.radians(azymut)
    return Kamera((cel[0] + promien * math.sin(a), cel[1] - promien * math.cos(a), wys), cel, ogniskowa)


def oswietlenie(n, P, kam):
    """Rozproszone (klucz), obrys pod światło (kontra), połysk. Światło stałe w świecie."""
    v = kam.pos[None, :] - P
    v /= np.linalg.norm(v, axis=1, keepdims=True)
    dif = np.clip(n @ KLUCZ, 0, 1)
    nv = np.abs(np.sum(n * v, 1))
    pod_swiatlo = np.clip(-(v @ KONTRA), 0, 1)
    rim = (1 - nv) ** 3 * (0.25 + 0.75 * pod_swiatlo)
    hv = KLUCZ[None, :] + v
    hv /= np.linalg.norm(hv, axis=1, keepdims=True)
    pol = np.clip(np.sum(n * hv, 1), 0, 1) ** 40
    return dif, rim, pol


def atmosfera(col, P, kam, mgla="#4A6AA6", d0=4.5, d1=11.0):
    d = np.linalg.norm(P - kam.pos[None, :], axis=1)
    f = np.clip((d - d0) / (d1 - d0), 0, 1)[:, None] * 0.4
    lum = col.mean(1, keepdims=True)
    return col * (1 - f) + rgb(mgla)[None, :] * lum * f * 1.4


def normalne(h, hx, hy, e):
    n = np.stack([-(hx - h) / e, -(hy - h) / e, np.ones_like(h)], 1)
    return n / np.linalg.norm(n, axis=1, keepdims=True)


def ekran(kam, P):
    """Rzut punktów + maska 'przed kamerą i w kadrze'."""
    P = np.atleast_2d(P)
    rel = P - kam.pos
    przod = rel @ kam.f > 0.05
    sx, sy, _ = kam.rzut(P)
    ok = przod & (sx > -50) & (sx < W + 50) & (sy > -50) & (sy < H + 50)
    return sx, sy, ok


def tlo_sceny(kam, gora="#03050C", dol="#0B1630", poswiata="#2A4A8A", sila=1.0):
    """Gradient nieba + poświata kontry (widoczna, gdy kamera patrzy pod światło)."""
    yy, xx = np.mgrid[0:H, 0:W].astype(np.float32)
    v = (yy / H)[..., None]
    img = rgb(gora) * (1 - v) + rgb(dol) * v
    d = ((xx - W / 2) / (W / 2)) ** 2 + ((yy - H / 2) / (H / 2)) ** 2
    img *= (1 - 0.45 * np.clip(d / 2, 0, 1))[..., None]
    sx, sy, ok = ekran(kam, kam.pos + KONTRA * 60)
    zrodlo = None
    if ok[0]:
        r = W * 0.45
        g = np.exp(-(((xx - sx[0]) / r) ** 2 + ((yy - sy[0]) / (r * 0.55)) ** 2))
        img += g[..., None] * rgb(poswiata) * 0.55 * sila
        zrodlo = (float(sx[0]), float(sy[0]))
    return img.astype(np.float32), zrodlo


def flara_obiektywu(zrodlo, sila=1.0):
    """Duchy obiektywu na linii źródło → środek kadru (tylko gdy kontra jest w kadrze lub blisko)."""
    out = np.zeros((H // 2, W // 2, 3), np.float32)
    if zrodlo is None:
        return cv2.resize(out, (W, H))
    lx, ly = zrodlo[0] / 2, zrodlo[1] / 2
    cx, cy = W / 4, H / 4
    for k, (r, kol, a) in enumerate(((60, "#3B6FD0", 0.05), (24, "#F2B046", 0.07), (90, "#2FC2C4", 0.03),
                                     (14, "#FFE3A3", 0.08), (40, "#7F5BD0", 0.04))):
        p = 0.45 + k * 0.42
        x, y = int(lx + (cx - lx) * p * 2), int(ly + (cy - ly) * p * 2)
        cv2.circle(out, (x, y), r, tuple(float(v) * a * sila for v in rgb(kol)), -1, cv2.LINE_AA)
    out = cv2.GaussianBlur(out, (0, 0), 6)
    return cv2.resize(out, (W, H))


def gwiazdki(xy, sila, kolor=ZLOTO_JASNE, dl=70):
    """Rozbłyski: jasny rdzeń + długie promienie poziome i krótsze pionowe (obliczane w ½ rozdzielczości)."""
    q = np.zeros((H // 2, W // 2, 3), np.float32)
    for (x, y), s in zip(xy, sila):
        if s > 0.01 and 0 <= x < W and 0 <= y < H:
            q[int(y / 2), int(x / 2)] += kolor * s
    if not q.any():
        return np.zeros((H, W, 3), np.float32)
    kh = np.exp(-np.abs(np.arange(-5 * dl, 5 * dl + 1)) / dl).astype(np.float32)[None, :]
    kv = np.exp(-np.abs(np.arange(-3 * dl // 2, 3 * dl // 2 + 1)) / (dl / 2.2)).astype(np.float32)[:, None]
    rdzen = cv2.GaussianBlur(q, (0, 0), 2.0) * 25 + cv2.GaussianBlur(q, (0, 0), 9) * 30
    prom = cv2.filter2D(q, -1, kh) * 0.9 + cv2.filter2D(q, -1, kv) * 0.6
    return cv2.resize(rdzen + prom, (W, H))


def wywolanie(tlo, em, ekspozycja=1.0, bloom=0.5, smuga=0.35, smuga_kol=LODOWY, ziarno=0.007, seed=0):
    """Tonemapping filmowy: emisja + poświata wieloskalowa + smuga anamorficzna z najjaśniejszych miejsc,
    złożone z tłem w trybie „screen”, lekka korekta kolorów (cienie granatowe, światła ciepłe), ziarno."""
    e = em * ekspozycja
    q = cv2.resize(e, (W // 4, H // 4), interpolation=cv2.INTER_AREA)
    bl = 0.6 * cv2.GaussianBlur(q, (0, 0), 3) + 0.35 * cv2.GaussianBlur(q, (0, 0), 10) + 0.25 * cv2.GaussianBlur(q, (0, 0), 30)
    jas = q.mean(2)
    prog = max(0.35, float(np.percentile(jas, 99.6)))
    hi = np.maximum(jas - prog, 0)
    sm = cv2.GaussianBlur(hi, (0, 0), sigmaX=70, sigmaY=0.7)[..., None] * smuga_kol
    dod = cv2.resize(bl * bloom + sm * smuga * 6, (W, H))
    img = 1 - np.exp(-(e + dod))
    out = 1 - (1 - tlo) * (1 - img)
    out = out + (1 - out) ** 6 * rgb("#050A1C") * 0.6          # cienie nie czarne, tylko granatowe
    out = out ** np.array([1.0, 0.98, 0.94], np.float32)        # światła lekko ciepłe
    rng = np.random.default_rng(seed + 99)
    out += (rng.random((H, W, 1), np.float32) - 0.5) * ziarno
    return np.clip(out, 0, 1)


def pyl(kam, t, c, N=30_000, R=3.2, z0=0.1, z1=1.8, seed=9, kolor=ZLOTO, sila=0.6):
    """Unoszący się złoty pył (bokeh dzięki głębi ostrości), migocze, rozbłyskuje po atakach."""
    r = np.random.default_rng(seed)
    rr = R * np.sqrt(r.random(N)); th = r.random(N) * 6.283
    z = z0 + np.mod(r.random(N) * (z1 - z0) + 0.03 * t, z1 - z0)
    mig = 0.5 + 0.5 * np.sin(r.random(N) * 6.28 + t * (1 + 2 * r.random(N)))
    w = (0.2 + mig) * (0.4 + 1.5 * c["impuls_ataku"] * (r.random(N) < 0.3)) * sila
    P = np.stack([rr * np.cos(th), rr * np.sin(th), z], 1)
    return splat(P, kolor[None, :] * w[:, None], kam, glebia=0.9)


def najwyzsze(kam, x, y, z, waga, siatka=10, ile=4):
    """Ekranowe położenia `ile` najjaśniejszych szczytów (po jednym na komórkę siatki xy)."""
    gx = np.clip(((x - x.min()) / (np.ptp(x) + 1e-9) * siatka).astype(int), 0, siatka - 1)
    gy = np.clip(((y - y.min()) / (np.ptp(y) + 1e-9) * siatka).astype(int), 0, siatka - 1)
    kom = gx * siatka + gy
    kolej = np.lexsort((-waga, kom))
    pierwsze = kolej[np.r_[True, kom[kolej][1:] != kom[kolej][:-1]]]
    naj = pierwsze[np.argsort(-waga[pierwsze])][:ile]
    sx, sy, ok = ekran(kam, np.stack([x[naj], y[naj], z[naj]], 1))
    return [(a, b) for a, b, o in zip(sx, sy, ok) if o], waga[naj][ok]


# ----------------------------------------------------------------------------- 1. wyspa poziomic
_BUF = {}


def _wyspa(N=3_000_000, R=3.3, e=0.008, seed=101):
    k = ("wyspa", N)
    if k not in _BUF:
        r = np.random.default_rng(seed)
        rr = R * np.sqrt(r.random(N)); th = r.random(N) * 2 * np.pi
        x = (rr * np.cos(th)).astype(np.float32); y = (rr * np.sin(th)).astype(np.float32)
        n1, n2, n3 = szum(r, 0.5), szum(r, 1.5), szum(r, 4.5)
        pola = []
        for ox, oy in ((0, 0), (e, 0), (0, e)):
            px, py = x + ox, y + oy
            a = n1(px + 10, py + 10)
            gory = 0.6 * a + 0.55 * np.clip(1 - np.abs(a) * 0.9, 0, 1) ** 2.5
            rad = np.hypot(px, py)
            brz = gladko(R, R * 0.5, rad)
            kop = 0.45 * np.exp(-(rad / 1.5) ** 2)
            pola.append(np.stack([(gory + kop) * brz, n2(px + 3, py) * brz, n3(px, py + 7) * brz], 1).astype(np.float32))
        _BUF.clear()
        _BUF[k] = (x, y, pola, e)
    return _BUF[k]


def _kregi_nut(analiza, t, okno=3.5):
    """Nuta → fala kolista na terenie. Środek: kąt ← klasa wysokości (12 kierunków), odległość ← oktawa."""
    out = []
    for ta, f, s in ostatnie_ataki(analiza, t, okno, 8):
        m = midi(f)
        kat = (round(m) % 12) / 12 * 2 * np.pi
        rho = 0.5 + 0.35 * np.clip((m - 48) / 12, 0, 3)
        out.append((rho * math.cos(kat), rho * math.sin(kat), t - ta, s))
    return out


def zloto_kontry(dif, rim, u, energia):
    """Ile złota: grzbiety oświetlone kluczem + krawędzie pod światło (jak na inspiracjach), × głośność."""
    g = (0.55 * np.clip(dif * 1.3 - 0.4, 0, 1) * u ** 0.6 + 1.6 * rim * (0.3 + 0.7 * u)) * (0.2 + 0.8 * energia)
    return np.clip(g, 0, 1) ** 2          # kwadrat: złoto tylko na krawędziach, reszta pozostaje łupkowo-granatowa


ZLOTE = ["#9A5A12", "#D88A22", "#F5B54A"]   # nasycone złoto (jasne odcienie przy tonemappingu i tak bieleją)


def _teren_wyspy(c, t, analiza, kam, N=3_000_000, linie=55, zloto_mn=1.0):
    x, y, pola, e = _wyspa(N)
    amp = np.array([0.30 + 0.55 * c["niskie"], 0.05 + 0.10 * c["srednie"], 0.012 + 0.02 * c["wysokie"]], np.float32)
    fale = _kregi_nut(analiza, t)
    hs = []
    for k, (ox, oy) in enumerate(((0, 0), (e, 0), (0, e))):
        h = pola[k] @ amp
        for cx, cy, wiek, s in fale:
            rf = 0.2 + 0.85 * wiek
            dx, dy = x + ox - cx, y + oy - cy
            m = np.flatnonzero(np.abs(dx) < rf + 0.5)
            d = np.hypot(dx[m], dy[m])
            h[m] += 0.035 * s * math.exp(-wiek / 1.6) * np.cos((d - rf) * 30) * np.exp(-((d - rf) / 0.18) ** 2)
        hs.append(h)
    h = hs[0]
    n = normalne(h, hs[1], hs[2], e)
    P = np.stack([x, y, h], 1)
    dif, rim, pol = oswietlenie(n, P, kam)
    lo, hi = np.percentile(h, [1, 99.5])
    u = np.clip((h - lo) / (hi - lo + 1e-6), 0, 1)
    lin = (0.5 + 0.5 * np.cos(2 * np.pi * h * linie)) ** 12
    wypelnienie = gradient(["#060B1A", "#12234A", "#2C4C84", "#6C8DC2"], u) * (0.25 + 0.75 * dif)[:, None]
    gz = np.clip(zloto_kontry(dif, rim, u, c["energia"]) * zloto_mn, 0, 1)
    kol_l = gradient(["#2E4168", "#7387AE"], dif) * (1 - gz[:, None]) + gradient(ZLOTE, gz) * gz[:, None]
    jas_l = 0.3 + 0.45 * dif + 1.6 * gz
    col = (wypelnienie * 0.14 + lin[:, None] * kol_l * jas_l[:, None] * 0.9
           + rim[:, None] * LODOWY * 0.12 + (pol * lin)[:, None] * ZLOTO_JASNE * 0.6)
    col *= gladko(3.3, 2.4, np.hypot(x, y))[:, None]          # brzeg wyspy gaśnie w ciemności
    col = atmosfera(col, P, kam)
    em = splat(P, col * 0.10, kam, glebia=0.35, warstwy=4)
    szczyty, wagi = najwyzsze(kam, x, y, h, h * (gz + 0.1))
    par = dict(gory=round(float(amp[0]), 3), fale=round(float(amp[1]), 3), kregi_nut=len(fale),
               zloto=round(0.35 + 1.3 * c["energia"], 3), linie_na_jednostke=linie)
    return em, szczyty, par


def k1_wyspa(c, t, analiza=None, azymut=20.0):
    """1. Wyspa poziomic: okrągła wyspa gór z gęstych warstwic (3 mln drobin). Bas → wysokość gór
    (więcej warstwic), głośność → złoto na oświetlonych grzbietach, nuta → fala kolista po terenie
    (kierunek ← nazwa dźwięku, odległość ← oktawa), atak → rozbłysk na najwyższym szczycie."""
    kam = kamera_orbita(azymut, promien=5.3, wys=2.0, cel=(0, 0, 0.3))
    tlo, zrodlo = tlo_sceny(kam)
    em, szczyty, par = _teren_wyspy(c, t, analiza, kam)
    em += pyl(kam, t, c)
    sila = 0.15 + 0.9 * c["impuls_ataku"] + 0.2 * c["energia"]
    em += gwiazdki(szczyty[:2], [sila, sila * 0.5])
    em += flara_obiektywu(zrodlo, 0.6 + c["energia"])
    par.update(rozblysk=round(sila, 3))
    return wywolanie(tlo, em, 1.0), par


# ----------------------------------------------------------------------------- 2. wstęga iskier
def k2_wstega(c, t, analiza=None, azymut=20.0):
    """2. Wstęga iskier: wstęga Möbiusa z 2 mln migoczących drobin krąży wokół środka sceny.
    Bas → falowanie w pionie, głośność → szerokość i jasność, wysokie tony → złote iskry na grzbietach
    fali, każda nuta → rozbłysk na krawędzi wstęgi (kąt ← nazwa dźwięku) i pióropusz iskier."""
    kam = kamera_orbita(azymut, promien=5.2, wys=1.6, cel=(0, 0, 0.0))
    tlo, zrodlo = tlo_sceny(kam, dol="#0A1430")
    r = np.random.default_rng(202)
    N = 2_000_000
    th = r.random(N) * 2 * np.pi + 0.04 * t
    u = r.random(N) * 2 - 1
    w = np.sign(u) * np.abs(u) ** 0.55
    faza, szyb, jas = r.random(N) * 6.283, 1 + 3 * r.random(N), r.lognormal(0, 1.2, N)

    def srodek(th):
        R = 2.0 + 0.25 * np.sin(2 * th + 0.3 * t)
        z = (0.22 + 0.4 * c["niskie"]) * np.sin(3 * th - 0.4 * t) + 0.12 * c["srednie"] * np.sin(5 * th + 0.7 * t)
        return R, z

    def punkt(th, w, pol):
        R, z = srodek(th)
        tw = 0.5 * th + 0.2 * t                       # pół obrotu na okrążenie: wstęga Möbiusa
        rx, ry = np.cos(th), np.sin(th)
        wx, wy, wz = np.cos(tw) * rx, np.cos(tw) * ry, np.sin(tw)
        return np.stack([R * rx + wx * w * pol, R * ry + wy * w * pol, z + wz * w * pol], 1), z
    pol = 0.28 + 0.4 * c["energia"]
    P, z = punkt(th, w, pol)
    P += r.standard_normal((N, 3)).astype(np.float32) * 0.008
    g = 0.5 + 0.5 * np.sin(th + 0.2 * t)
    kol = gradient(["#1E4FD8", "#2FB8E8", "#DDEBFF"], g)
    gz = (gladko(0.05, 0.4, z) * (0.3 + 1.2 * c["wysokie"]))[:, None]
    kol = kol * (1 - np.clip(gz, 0, 1)) + ZLOTO * np.clip(gz, 0, 1)
    krawedz = 0.35 + 0.9 * np.abs(w) ** 3
    mig = 0.55 + 0.45 * np.sin(faza + t * szyb)
    wag = jas * krawedz * mig * (0.35 + 0.9 * c["energia"])
    col = atmosfera(kol * wag[:, None], P, kam)
    em = splat(P, col * 0.035, kam, glebia=0.8, warstwy=5)
    # pióropusze iskier z krawędzi po nutach + rozbłyski
    flary, sily = [], []
    Ps, Cs = [], []
    for ta, f, s in ostatnie_ataki(analiza, t, 2.5, 8):
        wiek = t - ta
        kat = (round(midi(f)) % 12) / 12 * 2 * np.pi + 0.04 * t
        p0, _ = punkt(np.array([kat]), np.array([1.0]), pol)
        rr = np.random.default_rng(int(ta * 1000))
        n = 6000
        v = rr.standard_normal((n, 3)) * 0.35 + np.array([0, 0, 0.5])
        Ps.append(p0 + v * wiek ** 0.7)
        Cs.append(np.where(rr.random(n)[:, None] < 0.5, ZLOTO, rgb("#DDEBFF")) * (s * math.exp(-wiek / 0.9) * rr.lognormal(0, 1, n))[:, None])
        sx, sy, ok = ekran(kam, p0)
        if ok[0]:
            flary.append((sx[0], sy[0])); sily.append(s * math.exp(-wiek / 0.5) * 1.2)
    if Ps:
        em += splat(np.concatenate(Ps), np.concatenate(Cs) * 0.25, kam, glebia=0.8)
    # serce sceny: słaba złota mgławica w środku pulsująca z głośnością
    rs = np.random.default_rng(5)
    Pc = rs.standard_normal((150_000, 3)) * np.array([0.35, 0.35, 0.2])
    em += splat(Pc, ZLOTO[None, :] * (0.02 + 0.06 * c["energia"]) * rs.lognormal(0, 0.8, 150_000)[:, None], kam, glebia=0.8)
    em += gwiazdki(flary, sily)
    em += flara_obiektywu(zrodlo, 0.5 + c["energia"])
    return wywolanie(tlo, em, 1.0, smuga=0.45), dict(szerokosc=round(pol, 3), falowanie=round(0.22 + 0.4 * c["niskie"], 3),
                                                    zloto=round(0.3 + 1.2 * c["wysokie"], 3), pioropusze=len(Ps))


# ----------------------------------------------------------------------------- 3. góry ze strun
def _struny(ny=240, nx=10_000, R=3.3, e=0.008, seed=303):
    k = ("struny", ny, nx)
    if k not in _BUF:
        r = np.random.default_rng(seed)
        yr = np.linspace(-R, R, ny)
        x = np.tile(np.linspace(-R, R, nx), ny); y = np.repeat(yr, nx); wiersz = np.repeat(np.arange(ny), nx)
        ok = np.hypot(x, y) < R
        x, y, wiersz = x[ok].astype(np.float32), y[ok].astype(np.float32), wiersz[ok]
        x += (r.random(x.size).astype(np.float32) - 0.5) * 0.001
        n1, n2, n3 = szum(r, 0.6), szum(r, 1.8), szum(r, 6.0)
        pola = []
        for ox, oy in ((0, 0), (e, 0), (0, e)):
            px, py = x + ox, y + oy
            a = n1(px + 4, py + 4)
            gory = 0.45 * a + 0.75 * np.clip(1 - np.abs(a), 0, 1) ** 3
            brz = gladko(R, R * 0.6, np.hypot(px, py))
            pola.append(np.stack([gory * brz, n2(px, py) * brz, n3(px + 2, py) * brz], 1).astype(np.float32))
        # długość każdej struny (do drgań własnych): końce wiersza w kole
        pol = np.sqrt(np.maximum(R ** 2 - yr ** 2, 1e-6))
        _BUF.clear()
        _BUF[k] = (x, y, wiersz, pol, pola, e, ny)
    return _BUF[k]


_DAL = {}


def _lad_daleki(seed=313, R0=2.9, R1=15.0):
    """Ląd wokół gór ze strun: te same nici ciągną się aż do horyzontu, a na obrzeżu wyrasta pierścień
    wysokich, dalekich pasm (statyczny – nie gra, tylko daje przestrzeń). Normalne liczone raz."""
    if "lad" not in _DAL:
        r = np.random.default_rng(seed)
        ny, nx = 460, 4000
        yr = np.linspace(-R1, R1, ny)
        x = np.tile(np.linspace(-R1, R1, nx), ny); y = np.repeat(yr, nx)
        rad = np.hypot(x, y)
        ok = (rad > R0) & (rad < R1)
        x, y, rad = x[ok].astype(np.float32), y[ok].astype(np.float32), rad[ok]
        n1, n2 = szum(r, 0.22), szum(r, 0.8)
        e = 0.02

        def wys(px, py):
            pr = np.hypot(px, py)
            a = n1(px + 20, py + 20)
            gory = (0.35 * a + 0.9 * np.clip(1 - np.abs(a), 0, 1) ** 3) * (0.03 + 2.8 * gladko(6.5, 13.0, pr))
            return gory + 0.06 * n2(px, py) * gladko(R0, 5.0, pr)
        h = wys(x, y)
        n = normalne(h, wys(x + e, y), wys(x, y + e), e)
        _DAL["lad"] = (x, y, h.astype(np.float32), n.astype(np.float32), rad)
        G = 9000
        v = r.standard_normal((G, 3)); v[:, 2] = np.abs(v[:, 2]) * 0.9 + 0.03
        v /= np.linalg.norm(v, axis=1, keepdims=True)
        _DAL["gwiazdy"] = (v * 48, gradient(["#9CC4FF", "#FFFFFF", "#FFE3A3"], r.random(G)), r.lognormal(0, 1.0, G),
                           r.random(G) * 6.283, 0.5 + 2 * r.random(G))
    return _DAL["lad"], _DAL["gwiazdy"]


def zanik_przy_kamerze(P, kam, d0=1.0, d1=2.6):
    """Drobiny tuż przy obiektywie gasną (inaczej przelatujący ląd daje białe plamy)."""
    return gladko(d0, d1, np.linalg.norm(P - kam.pos[None, :], axis=1))


def przestrzen(kam, t, c, em):
    """Dalszy ląd i pasma, gwiazdy z migotaniem, księżyc nisko w kierunku kontry."""
    (x, y, h, n, rad), (G, kg, jg, fg, sg) = _lad_daleki()
    P = np.stack([x, y, h], 1)
    dif, rim, pol = oswietlenie(n, P, kam)
    u = np.clip(h / 2.6, 0, 1)
    baza = gradient(["#172848", "#2A416E", "#6A84B4"], (0.25 + 0.75 * u) * (0.35 + 0.65 * dif))
    gz = np.clip(rim * 1.6 * (0.2 + 0.8 * u), 0, 1) ** 2 * (0.4 + 0.6 * c["energia"])
    col = baza * (1 - gz[:, None]) + gradient(ZLOTE, gz) * gz[:, None] * 1.2
    col *= (gladko(2.9, 3.6, rad) * zanik_przy_kamerze(P, kam))[:, None]
    col = atmosfera(col, P, kam, d0=4.0, d1=16.0)
    # jasność × (odległość/ostrość)^1,2 – splat przyciemnia dalekie drobiny, a ląd ma być widoczny aż po horyzont
    d = np.linalg.norm(P - kam.pos[None, :], axis=1)
    kompens = np.clip(d / kam.ostrosc, 0.3, 3.0) ** 1.2
    em += splat(P, col * (0.12 * kompens * (1.8 - 0.8 * u))[:, None], kam, glebia=0.3, warstwy=3)
    mig = 0.6 + 0.4 * np.sin(fg + t * sg)
    em += splat(G, kg * (jg * mig * 14)[:, None], kam, glebia=0.0, warstwy=1)
    # księżyc: tarcza + halo, w kierunku kontry (świeci zza gór, gdy kamera patrzy pod światło)
    sx, sy, ok = ekran(kam, kam.pos + KONTRA * 60)
    if ok[0]:
        q = np.zeros((H // 2, W // 2, 3), np.float32)
        cv2.circle(q, (int(sx[0] / 2), int(sy[0] / 2)), 9, tuple(float(v) for v in rgb("#FFE9C2") * 3.0), -1, cv2.LINE_AA)
        q = cv2.GaussianBlur(q, (0, 0), 1.2) + cv2.GaussianBlur(q, (0, 0), 14) * 0.6 + cv2.GaussianBlur(q, (0, 0), 50) * 0.5
        em += cv2.resize(q, (W, H))
    return em


def kamera_struny(t, dlugosc):
    """Delikatna orbita: jedno okrążenie przez cały utwór, łagodny start i koniec (u − sin 2πu / 2π),
    powolny „oddech” odległości i wysokości. Maks. ~2,8°/s w połowie utworu."""
    u = float(np.clip(t / max(dlugosc, 1e-6), 0, 1))
    luk = u - math.sin(2 * math.pi * u) / (2 * math.pi)
    az = -25 + 360 * luk
    promien = 6.3 + 0.35 * math.sin(2 * math.pi * u * 1.5)
    wys = 1.75 + 0.28 * math.sin(2 * math.pi * u * 2 + 0.7)
    return kamera_orbita(az, promien=promien, wys=wys, cel=(0, 0, 0.32 + 0.05 * math.sin(2 * math.pi * u)))


def k3_struny(c, t, analiza=None, azymut=20.0, kam=None, z_przestrzenia=True):
    """3. Góry ze strun: pasmo gór utkane z 240 równoległych nici (~1,9 mln drobin) i mgła w dolinach.
    Każda nić to struna: nuta pobudza strunę o numerze ← wysokości dźwięku (88 klawiszy rozłożonych
    na nici), struna drga własnym drganiem (sin(kπx/L)) i świeci złotem, potem gaśnie.
    Przestrzeń: ląd z nici do horyzontu, pierścień dalekich pasm, gwiazdy, księżyc, warstwy mgły."""
    kam = kam or kamera_orbita(azymut, promien=6.0, wys=2.0, cel=(0, 0, 0.3))
    tlo, zrodlo = tlo_sceny(kam, poswiata="#3A5A9A")
    x, y, wiersz, dlug, pola, e, ny = _struny()
    amp = np.array([0.30 + 0.65 * c["niskie"], 0.04 + 0.08 * c["srednie"], 0.006 + 0.01 * c["wysokie"]], np.float32)
    hs = [p @ amp for p in pola]
    blask = np.zeros(len(x), np.float32)
    pobudzone = []
    for ta, f, s in ostatnie_ataki(analiza, t, 3.0, 10):
        wiek = t - ta
        k = int(np.clip((midi(f) - 21) / 87 * (ny - 1), 0, ny - 1))
        m = np.flatnonzero(np.abs(wiersz - k) <= 1)
        L = dlug[k]
        tryb = 1 + int(midi(f)) % 3
        dr = 0.06 * s * math.exp(-wiek / 1.2) * math.cos(2 * np.pi * 2.5 * wiek)
        for hh in hs:
            hh[m] += dr * np.sin(tryb * np.pi * (x[m] + L) / (2 * L)) * (1 - 0.5 * np.abs(wiersz[m] - k))
        blask[m] += s * math.exp(-wiek / 0.9) * (1 - 0.6 * np.abs(wiersz[m] - k))
        pobudzone.append(k)
    h = hs[0]
    n = normalne(h, hs[1], hs[2], e)
    P = np.stack([x, y, h], 1)
    dif, rim, pol = oswietlenie(n, P, kam)
    lo, hi = np.percentile(h, [1, 99.5])
    u = np.clip((h - lo) / (hi - lo + 1e-6), 0, 1)
    baza = gradient(["#0A1226", "#22365C", "#5C76A3", "#A9BCDB"], u * (0.3 + 0.7 * dif))
    gz = zloto_kontry(dif, rim, u, c["energia"])
    col = baza * (1 - gz[:, None]) + gradient(ZLOTE, gz) * gz[:, None] * 1.3
    col += rim[:, None] * LODOWY * 0.15 + pol[:, None] * ZLOTO_JASNE * 0.5
    col += np.clip(blask, 0, 1.5)[:, None] * ZLOTO_JASNE * 2.5
    col *= gladko(3.3, (2.8 if z_przestrzenia else 2.3), np.hypot(x, y))[:, None]
    col = atmosfera(col, P, kam)
    em = splat(P, col * 0.05, kam, glebia=0.35, warstwy=4)
    if z_przestrzenia:
        em = przestrzen(kam, t, c, em)
    # mgła: warstwy drobin nad dolinami, gęstość ← szum, dryfuje powoli (z przestrzenią sięga daleko)
    zas = 10.0 if z_przestrzenia else 3.3
    klucz = ("mgla", z_przestrzenia)
    if klucz not in _DAL:                        # gęstość liczona raz; cała mgła dryfuje razem z wiatrem
        r = np.random.default_rng(31)
        M = 1_000_000 if z_przestrzenia else 700_000
        mx0 = (r.random(M) * 2 - 1) * zas; my = (r.random(M) * 2 - 1) * zas
        mz = 0.02 + (0.3 if z_przestrzenia else 0.16) * r.random(M) ** 2
        g0 = np.clip(szum(np.random.default_rng(32), 0.6 if z_przestrzenia else 1.2)(mx0, my) * 0.6 + 0.3, 0, 1) ** 2
        _DAL[klucz] = (mx0, my, mz, g0)
    mx0, my, mz, g0 = _DAL[klucz]
    mx = np.mod(mx0 + 0.04 * t + zas, 2 * zas) - zas
    gest = g0 * gladko(zas, zas * 0.65, np.hypot(mx, my))
    Pm = np.stack([mx, my, mz], 1)
    if z_przestrzenia:
        gest *= zanik_przy_kamerze(Pm, kam, 1.5, 3.5)
    em += splat(Pm, rgb("#9FB7DA")[None, :] * (gest * 0.03 * (0.6 + 0.6 * c["energia"]))[:, None], kam, glebia=0.6)
    em += pyl(kam, t, c, N=20_000, R=4.2 if z_przestrzenia else 3.2, sila=0.4)
    szczyty, _ = najwyzsze(kam, x, y, h, h * (gz + 0.05) + blask * 0.3)
    sila = 0.1 + 0.8 * c["impuls_ataku"]
    em += gwiazdki(szczyty[:1], [sila])
    em += flara_obiektywu(zrodlo, 0.7 + c["energia"])
    return wywolanie(tlo, em, 1.0), dict(gory=round(float(amp[0]), 3), struny_pobudzone=pobudzone,
                                        zloto=round(0.35 + 1.4 * c["energia"], 3))


# ----------------------------------------------------------------------------- 4. dolina nokturnu
def k4_dolina(c, t, analiza=None, azymut=20.0):
    """4. Dolina nokturnu (połączenie): wyspa poziomic (2,2 mln), nad nią łuk rzeki iskier jak Droga
    Mleczna (0,9 mln; jasność i szerokość ← wysokie tony), sfera gwiazd daleko (paralaksa przy obrocie),
    złoty pył. Ataki: rozbłyski na szczytach i na łuku."""
    kam = kamera_orbita(azymut, promien=6.6, wys=1.9, cel=(0, 0, 0.8), ogniskowa=1.2)
    tlo, zrodlo = tlo_sceny(kam, dol="#0C1A38")
    em, szczyty, par = _teren_wyspy(c, t, analiza, kam, N=2_200_000)
    r = np.random.default_rng(404)
    N = 900_000
    s = np.mod(r.random(N) + 0.012 * t, 1.0)
    phi = math.radians(35)
    rad = 3.6 * np.cos(np.pi * (s - 0.5) * 1.05)
    wzn = 2.7 * np.sin(np.pi * s * 1.0) - 0.2
    xx = rad * 0 + (s - 0.5) * 7.4
    pos = np.stack([xx * math.cos(phi), xx * math.sin(phi), wzn], 1)
    szer = 0.12 + 0.2 * c["wysokie"]
    pos += r.standard_normal((N, 3)) * np.array([szer * 0.6, szer * 0.6, szer])
    kol = np.where(r.random(N)[:, None] < 0.45, ZLOTO, gradient(["#3F7FE8", "#2FC2C4", "#E6F0FF"], r.random(N)))
    mig = 0.55 + 0.45 * np.sin(r.random(N) * 6.28 + t * 2.5)
    em += splat(pos, kol * (r.lognormal(0, 1.5, N) * mig * (0.012 + 0.03 * c["wysokie"]))[:, None], kam, glebia=0.3)
    # gwiazdy daleko
    G = 6000
    v = r.standard_normal((G, 3)); v[:, 2] = np.abs(v[:, 2]) + 0.05
    v /= np.linalg.norm(v, axis=1, keepdims=True)
    em += splat(v * 30, gradient(["#9CC4FF", "#FFFFFF", "#FFE3A3"], r.random(G)) * (r.lognormal(0, 1, G) * 2.5)[:, None], kam, glebia=0.0, warstwy=1)
    em += pyl(kam, t, c, N=20_000)
    sila = 0.15 + 0.9 * c["impuls_ataku"] + 0.2 * c["energia"]
    em += gwiazdki(szczyty[:2], [sila, sila * 0.5])
    em += flara_obiektywu(zrodlo, 0.6 + c["energia"])
    par.update(luk_szerokosc=round(szer, 3), rozblysk=round(sila, 3))
    return wywolanie(tlo, em, 1.0), par


# ----------------------------------------------------------------------------- 5. membrana Bessela
def _membrana(N=3_000_000, R=2.6, e=0.008, seed=505):
    k = ("membrana", N)
    if k not in _BUF:
        r = np.random.default_rng(seed)
        rr = R * np.sqrt(r.random(N)); th = r.random(N) * 2 * np.pi
        x = (rr * np.cos(th)).astype(np.float32); y = (rr * np.sin(th)).astype(np.float32)
        pol = [(np.hypot(x + ox, y + oy), np.arctan2(y + oy, x + ox)) for ox, oy in ((0, 0), (e, 0), (0, e))]
        _BUF.clear()
        _BUF[k] = (x, y, pol, e, R)
    return _BUF[k]


def k5_membrana(c, t, analiza=None, azymut=20.0):
    """5. Membrana Bessela: okrągła membrana (3 mln drobin) drga jak bęben / płyta rezonansowa.
    Kształt = suma drgań własnych J_m(k·r)·cos(m·θ): każdy z 3 najsilniejszych szczytów widma wybiera
    tryb (m ← nazwa dźwięku, n ← oktawa), amplituda ← siła szczytu × głośność; tryby obracają się powoli.
    Gęste warstwice tworzą „odcisk palca”, piasek zbiera się na liniach węzłowych (jak figury Chladniego),
    nuty wysyłają fale koliste ze środka. Matematyka wprost: funkcje Bessela."""
    kam = kamera_orbita(azymut, promien=5.0, wys=1.9, cel=(0, 0, 0.1))
    tlo, zrodlo = tlo_sceny(kam, dol="#0A1230", poswiata="#3A3F9A")
    x, y, pol, e, R = _membrana()
    mody = []
    if analiza is not None:
        for f, a in analiza.szczyty(t, n=3):
            mm = midi(f)
            m = int(round(mm)) % 12 % 5
            nn = 1 + (int(round(mm)) // 12) % 3
            mody.append((m, nn, a * (0.05 + 0.16 * c["energia"]), 0.25 * t * (1 if m % 2 else -1) + mm * 0.5))
    hs = []
    tab_r = np.linspace(0, R * 1.01, 4096)                    # J_m zależy tylko od r → tablica + interpolacja
    for rr, th in pol:
        h = (0.06 + 0.16 * c["niskie"]) * np.interp(rr, tab_r, jv(0, 2.4048 * tab_r / R))
        for m, nn, a, rot in mody:
            h += a * np.interp(rr, tab_r, jv(m, jn_zeros(m, nn)[-1] * tab_r / R)) * np.cos(m * th + rot)
        for ta, f, s in ostatnie_ataki(analiza, t, 3.0, 8):
            wiek = t - ta
            rf = 0.1 + 0.9 * wiek
            mk = np.flatnonzero(np.abs(rr - rf) < 0.6)
            h[mk] += 0.03 * s * math.exp(-wiek / 1.5) * np.cos((rr[mk] - rf) * 28) * np.exp(-((rr[mk] - rf) / 0.2) ** 2)
        hs.append(h.astype(np.float32))
    h = hs[0]
    n = normalne(h, hs[1], hs[2], e)
    P = np.stack([x, y, h], 1)
    dif, rim, pl = oswietlenie(n, P, kam)
    sk = max(float(np.percentile(np.abs(h), 99)), 0.02)
    u = np.clip(0.5 + 0.5 * h / sk, 0, 1)
    kol = gradient(["#140F45", "#233E8C", "#3C78C8", "#E9C27A", "#FFE6A8"], u)
    # warstwice co stały ułamek amplitudy: zawsze ~20 linii, czytelne także w cichych fragmentach
    lin = (0.5 + 0.5 * np.cos(2 * np.pi * h / sk * 10)) ** 10
    gz = zloto_kontry(dif, rim, u, c["energia"])
    kol = kol * (1 - gz[:, None] * 0.8) + gradient(ZLOTE, gz) * gz[:, None] * 0.8
    col = kol * (0.08 + 0.12 * dif)[:, None] + lin[:, None] * kol * (0.4 + 0.6 * dif + 0.6 * gz)[:, None]
    col += rim[:, None] * LODOWY * 0.15 + (pl * lin)[:, None] * ZLOTO_JASNE * 0.8
    # piasek na liniach węzłowych (|h| ≈ 0) – lekko uniesiony, biały
    wezly = np.exp(-(h / (0.06 * sk)) ** 2) * (len(mody) > 0)
    col += wezly[:, None] * rgb("#E8EEFF") * 0.35
    col = atmosfera(col, P, kam)
    em = splat(P, col * 0.05, kam, glebia=0.35, warstwy=4)
    # złota obręcz membrany
    rb = np.random.default_rng(6)
    tb = rb.random(80_000) * 2 * np.pi
    Pb = np.stack([R * np.cos(tb), R * np.sin(tb), rb.standard_normal(80_000) * 0.006], 1)
    em += splat(Pb, ZLOTO[None, :] * (0.2 + 0.5 * c["energia"]) * np.ones((80_000, 1)) * 0.25, kam, glebia=0.35)
    em += pyl(kam, t, c, N=15_000, R=2.8, sila=0.4)
    szczyty, _ = najwyzsze(kam, x, y, h, h * lin, siatka=8)
    sila = 0.1 + 0.9 * c["impuls_ataku"]
    em += gwiazdki(szczyty[:2], [sila, sila * 0.6])
    em += flara_obiektywu(zrodlo, 0.5 + c["energia"])
    return wywolanie(tlo, em, 1.0), dict(mody=[(m, nn, round(a, 4)) for m, nn, a, _ in mody],
                                        bas_j0=round(0.06 + 0.16 * c["niskie"], 3))


# ścieżki kamery dla pełnych klipów: f(t, długość utworu) -> Kamera
SCIEZKI_KAMERY = {"3_gory_ze_strun": kamera_struny}

KONCEPCJE_V2 = {
    "1_wyspa_poziomic": k1_wyspa,
    "2_wstega_iskier": k2_wstega,
    "3_gory_ze_strun": k3_struny,
    "4_dolina_nokturnu": k4_dolina,
    "5_membrana_bessela": k5_membrana,
}
