"""„Piasek fraktalny”: makro-powierzchnia piasku (wydmy, koncentryczne grzbiety, spiralne zagłębienia,
wieloskalowe wiry) sterowana pomiarem nagrania. Kamera stała, nisko nad powierzchnią, światło pod małym kątem.

Mapowanie dźwięk → obraz (pomiar z `analiza.py`, parametry liczone raz dla całej osi czasu):
  niskie (30–250 Hz)   → wysokość i przesuw szerokich wydm, głębokość zagłębień; poświata POMARAŃCZOWA
  średnie (250–2000 Hz) → interferencje pierścieni, siła i obrót wirów (grzbiety spiral)
  wysokie (2–8 kHz)     → drobne zmarszczki, iskrzenie i unoszenie ziaren; poświata NIEBIESKA
  ataki                 → pierścień-impuls rozchodzący się po powierzchni od środka wiru
  wybrzmienie           → obwiednie opadają powoli (zanik ~0,6–1 s), ruch się uspokaja
  złożoność (bogactwo brzmienia: liczba klas wysokości + średnie pasmo) → udział kolejnych poziomów
  fraktala wirów (nie rośnie z czasem – tylko z dźwiękiem)
Fazy ruchu to całki z energii (ruch zwalnia w ciszy, nigdy nie skacze). Szum i ziarna są stałe w świecie,
więc ciągłość geometrii i faktury jest zachowana między klatkami.
"""
import math

import numpy as np

W, H = 1280, 720          # wyjście
SS = 1.5                  # nadpróbkowanie (mniej migotania drobnych błysków)
FPS = 25

# paleta
TLO_DAL = np.array([0.006, 0.008, 0.022])     # granat prawie czarny (daleko)
TLO_BLISKO = np.array([0.012, 0.010, 0.022])
SZAMPAN = np.array([0.93, 0.79, 0.60])
MIEDZ = np.array([0.80, 0.47, 0.28])
ROZ_ZLOTO = np.array([0.86, 0.60, 0.58])
POMARANCZ = np.array([1.00, 0.52, 0.16])      # niskie tony
NIEBIESKI = np.array([0.36, 0.64, 1.00])      # wysokie tony


def _ema(x, tau, fps=FPS):
    k = 1 - math.exp(-1 / (tau * fps))
    y = np.empty_like(x); s = x[0]
    for i, v in enumerate(x):
        s += k * (v - s); y[i] = s
    return y


def _gl(a, b, x):
    t = np.clip((x - a) / (b - a), 0, 1)
    return t * t * (3 - 2 * t)


def parametry(an, n, fps=FPS):
    """Parametry klatek 0..n-1 z pomiaru (deterministyczne; każda klatka liczona niezależnie)."""
    t = np.arange(n) / fps
    i = np.clip(np.round(t * 22050 / 512).astype(int), 0, len(an.czas) - 1)
    L, M, Hh = (an.pasma_env[k, i] for k in range(3))
    E = an.rms_env[i]
    ch = an.chroma[:, i]
    ch = ch / (ch.max(0, keepdims=True) + 1e-9)
    bogactwo = (ch > 0.45).sum(0) / 7.0
    # geometria: dodatkowe wygładzenie (bez szarpania), ale atak nadal widoczny przez impulsy
    Ls, Ms, Hs = _ema(L, 0.25), _ema(M, 0.2), _ema(Hh, 0.12)
    zloz = _ema(np.clip(0.55 * Ms + 0.45 * bogactwo, 0, 1.2), 0.6)
    # fazy = całki z energii (ruch zwalnia w ciszy)
    faza_L = np.cumsum(0.10 + 0.55 * Ls) / fps
    faza_M = np.cumsum(0.15 + 1.10 * Ms) / fps
    faza_H = np.cumsum(0.20 + 1.60 * Hs) / fps
    ataki = [(float(ta), float(an.atak[an.idx(ta)])) for ta in an.ataki]
    return dict(t=t, L=Ls, M=Ms, H=Hs, E=_ema(E, 0.15), zloz=zloz, fL=faza_L, fM=faza_M, fH=faza_H, ataki=ataki)


# ----------------------------------------------------------------------------- świat (stały)
class Swiat:
    def __init__(self, seed=20261123, w=int(W * SS), h=int(H * SS)):
        self.w, self.h = w, h
        r = np.random.default_rng(seed)
        v = (np.arange(h) + 0.5) / h                    # 0 = góra kadru (daleko), 1 = dół (blisko)
        u = (np.arange(w) + 0.5) / w - 0.5
        # perspektywa: kamera nisko, patrzy ukośnie w dół; głębokość rośnie ku górze kadru
        z = 1.0 / (0.16 + 0.84 * v)                     # 1 (blisko) .. ~6 (daleko)
        self.Z = np.repeat(z[:, None], w, 1).astype(np.float32)
        self.X = (u[None, :] * 1.78 * 2.2 * self.Z).astype(np.float32)
        self.Y = (self.Z * 2.0).astype(np.float32)
        self.dpx = (1.78 * 2.2 * self.Z / w).astype(np.float32)        # metry świata na piksel (poziomo)
        dz = np.gradient(z * 2.0)
        self.dpy = np.repeat(np.abs(dz)[:, None], w, 1).astype(np.float32)
        # pole zawirowań (stałe) – domena organiczna
        self.fale_w = [(r.uniform(0, 2 * np.pi), r.uniform(0.25, 0.7), r.uniform(0, 2 * np.pi)) for _ in range(6)]
        # ziarna: stały szum w pikselach (makro – ziarno ~1–2 px), kolor ziarna
        self.ziarno = r.random((h, w), dtype=np.float32)
        self.ziarno2 = r.random((h, w), dtype=np.float32)
        mix = r.random((h, w), dtype=np.float32)
        self.kolor = (SZAMPAN[None, None] * (1 - mix[..., None]) * 0.55 + MIEDZ[None, None] * mix[..., None] * 0.6
                      + ROZ_ZLOTO[None, None] * (r.random((h, w), dtype=np.float32)[..., None] * 0.35)).astype(np.float32)
        self.kolor /= self.kolor.max(-1, keepdims=True).clip(1e-3) / np.array([1.0], np.float32)
        # wiry: fraktal 3 poziomów (środek, promień, liczba ramion, kierunek)
        self.wiry = []
        glowne = [(-1.4, 5.2, 2.3), (1.9, 7.0, 2.8), (0.2, 9.8, 3.2), (-3.6, 9.0, 2.6), (3.9, 3.6, 1.5)]
        for cx, cy, R in glowne:
            self.wiry.append((0, cx, cy, R, r.choice([2, 3]), r.choice([-1, 1])))
            for k in range(3):
                a = r.uniform(0, 2 * np.pi); d = R * r.uniform(0.75, 1.15)
                c1 = (cx + d * math.cos(a), cy + d * math.sin(a) * 0.8)
                self.wiry.append((1, c1[0], c1[1], R * 0.38, r.choice([1, 2]), r.choice([-1, 1])))
                for j in range(2):
                    b = r.uniform(0, 2 * np.pi); e = R * 0.38 * r.uniform(0.8, 1.2)
                    self.wiry.append((2, c1[0] + e * math.cos(b), c1[1] + e * math.sin(b) * 0.8, R * 0.14, 1,
                                      r.choice([-1, 1])))
        # ataki startują z wirów dobrze widocznych w kadrze (bliski środek, prawy przód, środek dalej)
        self.zrodla_atakow = [(glowne[i][0], glowne[i][1]) for i in (0, 4, 1)]


def _wir(X, Y, cx, cy, R, ramiona, kier, faza, glebia):
    dx, dy = X - cx, (Y - cy) * 1.25
    r2 = dx * dx + dy * dy
    r = np.sqrt(r2) + 1e-4
    th = np.arctan2(dy, dx)
    lam = R * 0.085
    spir = (0.5 + 0.5 * np.sin(2 * np.pi * r / lam + kier * ramiona * th - faza)) ** 5 - 0.25
    otoczka = np.exp(-r2 / (R * R * 1.1)) * (1 - np.exp(-r2 / (R * R * 0.012)))
    lejek = -glebia * np.exp(-r2 / (R * R * 0.10))
    return spir * otoczka, lejek


def klatka(sw: Swiat, p, k):
    """Obraz float32 (h, w, 3), 0..1, w nadpróbkowanej rozdzielczości."""
    t = p["t"][k]; L, M, Hh, E, zl = p["L"][k], p["M"][k], p["H"][k], p["E"][k], p["zloz"][k]
    fL, fM, fH = p["fL"][k], p["fM"][k], p["fH"][k]
    X = sw.X + 0.035 * t                     # bardzo powolny dryf kamery
    Y = sw.Y
    # domena organiczna (wolno płynie z fazą niskich)
    wx = np.zeros_like(X); wy = np.zeros_like(X)
    for a, kk, f0 in sw.fale_w:
        arg = kk * (X * math.cos(a) + Y * math.sin(a)) + f0 + 0.25 * fL
        wx += 0.35 * np.sin(arg); wy += 0.35 * np.cos(arg * 1.3 + 1.0)
    Xw, Yw = X + wx, Y + wy
    # 1) wydmy – niskie
    wyd = (np.sin(0.55 * Xw + 0.9 * Yw * 0.6 - 0.8 * fL) * 0.9 + np.sin(0.31 * Xw - 0.47 * Yw + 0.5 * fL + 1.7) * 0.7
           + np.sin(0.83 * Yw + 0.2 * Xw - 0.6 * fL) * 0.45)
    A_wyd = 0.16 + 0.50 * L
    h = A_wyd * wyd
    # 2) wiry fraktalne + interferencje – średnie, złożoność
    wagi = (1.0, float(_gl(0.25, 0.65, zl)), float(_gl(0.5, 0.95, zl)))
    A_wir = 0.020 + 0.050 * M
    spir_sum = np.zeros_like(X); lej = np.zeros_like(X)
    for poz, cx, cy, R, ram, kier in sw.wiry:
        wg = wagi[poz]
        if wg < 0.02:
            continue
        s, lj = _wir(Xw, Yw, cx, cy, R, ram, kier, fM * (1.8 + poz), glebia=0.12 + 0.45 * L if poz == 0 else 0.06)
        spir_sum += wg * s * (1.0 if poz == 0 else 0.75)
        lej += wg * lj
    h += A_wir * spir_sum + lej
    (c1x, c1y), (c2x, c2y) = sw.zrodla_atakow[0], sw.zrodla_atakow[1]
    r1 = np.hypot(Xw - c1x, (Yw - c1y) * 1.2); r2 = np.hypot(Xw - c2x, (Yw - c2y) * 1.2)
    h += (0.006 + 0.020 * M) * ((0.5 + 0.5 * np.sin(11 * r1 - 2.2 * fM)) ** 4 + (0.5 + 0.5 * np.sin(11 * r2 - 2.0 * fM)) ** 4) * np.exp(-0.08 * (r1 + r2))
    # 3) drobne zmarszczki – wysokie
    lata = np.clip(0.5 + 0.7 * np.sin(0.9 * Xw + 0.3) * np.sin(0.7 * Yw - 0.2 * Xw), 0, 1)
    zm = np.sin(42.0 * (Xw * 0.8 + Yw * 0.6) + 3.0 * np.sin(1.3 * Yw + 0.4 * Xw) + 1.2 * wyd - 1.5 * fH) * lata
    A_zm = 0.0012 + 0.0045 * Hh
    h += A_zm * zm
    makro = A_wyd * wyd + lej
    # 4) impulsy ataków: pierścień od środka głównego wiru (deterministycznie wg numeru ataku)
    imp = np.zeros_like(X)
    for j, (ta, sila) in enumerate(p["ataki"]):
        dt = t - ta
        if dt < 0 or dt > 2.2:
            continue
        cx, cy = sw.zrodla_atakow[j % len(sw.zrodla_atakow)]
        rr = np.hypot(Xw - cx, (Yw - cy) * 1.2)
        front = 0.25 + 2.6 * dt
        imp += (0.35 + 0.65 * sila) * np.exp(-((rr - front) / 0.13) ** 2) * math.exp(-dt / 0.65) * np.exp(-0.12 * rr)
    h += 0.15 * imp

    # normalne i światło pod małym kątem (z lewej, z tyłu)
    gy, gx = np.gradient(h)
    hx = gx / sw.dpx; hy = gy / sw.dpy
    nz = 1.0 / np.sqrt(1 + hx * hx + hy * hy)
    nx, ny = -hx * nz, hy * nz
    Ld = np.array([-0.80, 0.42, 0.28]); Ld = Ld / np.linalg.norm(Ld)
    dif = np.clip(nx * Ld[0] + ny * Ld[1] + nz * Ld[2], 0, None)
    grzbiet = _gl(0.25, 0.97, dif) ** 1.7
    my, mx = np.gradient(makro)
    mhx = mx / sw.dpx; mhy = my / sw.dpy
    mnz = 1.0 / np.sqrt(1 + mhx * mhx + mhy * mhy)
    dif_m = np.clip(-mhx * mnz * Ld[0] + mhy * mnz * Ld[1] + mnz * Ld[2], 0, None)
    cien = 0.18 + 1.05 * _gl(0.05, 0.85, dif_m)       # światło na stokach wydm (makro)
    # ziarnistość: jasność pojedynczych ziaren (stała), połysk zależy od nachylenia (zmienia się płynnie)
    gr = sw.ziarno
    blysk = np.clip((gr - 0.978) / 0.022, 0, 1) * _gl(0.45, 0.95, dif) ** 2
    # unoszenie ziaren przy wysokich: rzadkie jasne drobiny nad grzbietami
    unos = np.clip((sw.ziarno2 - (0.9993 - 0.0025 * Hh)) / 0.0025, 0, 1) * (0.25 + grzbiet)
    tekstura = 0.30 + 1.35 * gr ** 3 + 0.25 * sw.ziarno2

    gl = np.clip(sw.Z / 6.0, 0, 1)[..., None]
    tlo = TLO_BLISKO * (1 - gl) + TLO_DAL * gl
    swiatlo = ((0.015 + 0.95 * grzbiet + 0.08 * dif) * cien)[..., None] * tekstura[..., None] * sw.kolor
    # poświata pasm: niskie → pomarańcz na stokach wydm, wysokie → błękit w drobnym detalu
    wyd_n = np.clip(0.5 + 0.5 * wyd / 2.0, 0, 1)
    kol_L = POMARANCZ * (1.4 * L ** 1.6) * (grzbiet * cien * (0.3 + 0.7 * wyd_n) * tekstura)[..., None]
    detal = np.clip(zm, 0, 1) ** 3 * grzbiet * tekstura
    kol_H = NIEBIESKI * (1.6 * Hh ** 1.6) * (1.2 * detal + 3.0 * blysk + 2.5 * unos)[..., None]
    kol_imp = (SZAMPAN * 0.6 + NIEBIESKI * 0.4 * Hh) * (1.3 * imp * (0.35 + grzbiet) * tekstura)[..., None]
    # barwa świateł wg pasm: niskie ocieplają ku pomarańczy, wysokie chłodzą ku błękitowi
    grade = (1 + 0.85 * L ** 2 * (POMARANCZ / POMARANCZ.mean() - 1)
             + 0.95 * Hh ** 2 * (NIEBIESKI / NIEBIESKI.mean() - 1))
    grade = np.clip(grade, 0.15, None)
    grade = grade / (0.30 * grade[0] + 0.59 * grade[1] + 0.11 * grade[2])   # bez zmiany jasności
    swiatlo = swiatlo * grade
    obraz = tlo + swiatlo * (0.80 + 0.35 * E) + kol_L + kol_H + kol_imp + SZAMPAN * 1.4 * blysk[..., None]
    obraz += SZAMPAN * 1.2 * unos[..., None]
    obraz *= (1 - 0.55 * gl ** 1.5)           # spadek światła w głębi
    return obraz.astype(np.float32)


def wywolaj(obraz, sw: Swiat):
    """Głębia ostrości (daleko i bardzo blisko miękko), tonemapping, winieta, skala do 1280×720."""
    import cv2
    rozm = [obraz]
    for s in (1.2, 2.6):
        rozm.append(cv2.GaussianBlur(obraz, (0, 0), s))
    v = np.linspace(0, 1, obraz.shape[0])[:, None, None]
    ostr = np.exp(-((v - 0.74) / 0.26) ** 2)       # płaszczyzna ostrości w 2/3 wysokości
    b1 = np.clip(1 - ostr, 0, 1)
    wynik = rozm[0] * ostr + (rozm[1] * (1 - b1 ** 2) + rozm[2] * b1 ** 2) * (1 - ostr)
    blask = cv2.GaussianBlur(np.clip(wynik - 0.6, 0, None), (0, 0), 6)
    wynik = wynik + 0.35 * blask
    wynik = 1 - np.exp(-1.6 * wynik)              # tonemapping
    yy, xx = np.mgrid[0:obraz.shape[0], 0:obraz.shape[1]]
    win = 1 - 0.38 * (((xx / obraz.shape[1] - 0.5) * 1.1) ** 2 + ((yy / obraz.shape[0] - 0.55) * 1.3) ** 2)
    wynik *= win[..., None]
    wynik = cv2.resize(wynik, (W, H), interpolation=cv2.INTER_AREA)
    return (np.clip(wynik, 0, 1) ** (1 / 1.08) * 255 + 0.5).astype(np.uint8)
