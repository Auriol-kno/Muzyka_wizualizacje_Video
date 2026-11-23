"""„Piasek fraktalny 3D”: ~3,5 mln ziaren piasku w przestrzeni, kamera nisko nad powierzchnią.
Wysokość każdego ziarna liczona z pomiaru nagrania – wzgórza fizycznie rosną i opadają w kadrze.

Mapowanie dźwięk → obraz (prośba właściciela 2026-11-23):
  WYSOKIE tony → dodatnia amplituda: piasek wypiętrza się w wzgórza i szczyty; barwa POMARAŃCZOWA
  NISKIE tony / bas → ujemna amplituda: leje i doliny zapadają się; barwa NIEBIESKA
  każdy dźwięk: widmo dzielone na półtony (MIDI 36–95); każdy półton ma stałe miejsce na powierzchni
    (wysokość dźwięku → położenie w poprzek kadru, klasa wysokości → głębokość) i wybrzusza piasek
    w górę (wysokie) albo w dół (niskie) z koncentryczną zmarszczką – widać każdą nutę
  średnie → obrót i siła spiralnych grzbietów wirów; ataki → pierścień-fala od środka sceny
  mienienie się: każde ziarno ma własną mikrościankę obracającą się powoli; błysk, gdy ścianka odbija
    światło do kamery (szybciej i częściej przy wysokich tonach i po atakach)
Obwiednie: atak ~30 ms, zanik 0,35–0,6 s; geometria bez skoków (wszystko z obwiedni i całek energii).
"""
import math

import cv2
import numpy as np

from wizualizacje.analiza import obwiednia
from wizualizacje.czasteczki import H, W, Kamera, rgb

W_OUT, H_OUT = 1280, 720
FPS = 25
AMPLITUDA = 1.2        # mnożnik całej wysokości piasku (właściciel: +20%)

SZAMPAN, MIEDZ, ROZ = rgb("#EBCB9C"), rgb("#C07A48"), rgb("#D9A39A")
POMARANCZ, NIEBIESKI = rgb("#FF8A2A"), rgb("#3F8CFF")
TLO_GORA, TLO_DOL = rgb("#020309"), rgb("#070B1C")
SWIATLO = np.array([-0.82, 0.35, 0.34]); SWIATLO /= np.linalg.norm(SWIATLO)   # nisko, z lewej


def _ema(x, tau, fps=FPS):
    k = 1 - math.exp(-1 / (tau * fps))
    y = np.empty_like(x); s = x[0]
    for i, v in enumerate(x):
        s += k * (v - s); y[i] = s
    return y


# ----------------------------------------------------------------------------- parametry z dźwięku
M0, M1 = 36, 96                                   # półtony C2..B6


def parametry(an, n, fps=FPS):
    t = np.arange(n) / fps
    i = np.clip(np.round(t * 22050 / 512).astype(int), 0, len(an.czas) - 1)
    L, M, Hh = (an.pasma_env[k, i] for k in range(3))
    # widmo półtonowe (cała oś ramek analizy), obwiednia: szybki atak, łagodny zanik
    m = 12 * np.log2(np.maximum(an.freqs, 1) / 440) + 69
    b = np.round(m).astype(int)
    pol = np.zeros((M1 - M0, an.mag.shape[1]), np.float32)
    for k in range(M1 - M0):
        sel = b == M0 + k
        if sel.any():
            pol[k] = an.mag[sel].max(0)
    pol = np.sqrt(pol)
    pol /= np.percentile(pol.max(0), 97) + 1e-9
    pol = np.clip(pol - 0.18, 0, None) / 0.82            # próg szumu
    pol = np.array([obwiednia(r, atak=0.03, zanik=0.45) for r in pol])
    nuty = pol[:, i].T                                   # (n, półtony)
    fL = np.cumsum(0.15 + 0.8 * _ema(L, 0.2)) / fps
    fM = np.cumsum(0.2 + 1.6 * _ema(M, 0.15)) / fps
    fH = np.cumsum(0.4 + 3.0 * _ema(Hh, 0.1)) / fps
    ataki = [(float(ta), float(an.atak[an.idx(ta)])) for ta in an.ataki]
    return dict(t=t, L=_ema(L, 0.12), M=_ema(M, 0.12), H=_ema(Hh, 0.08), E=_ema(an.rms_env[i], 0.1),
                nuty=nuty, fL=fL, fM=fM, fH=fH, ataki=ataki, dl=n / fps)


# ----------------------------------------------------------------------------- świat
class Swiat:
    def __init__(self, seed=20261123, nx=2600, ny=1700):
        r = np.random.default_rng(seed)
        self.nx, self.ny = nx, ny
        u = (np.arange(nx) + 0.5) / nx
        v = (np.arange(ny) + 0.5) / ny
        x = -7.0 + 14.0 * u
        y = -2.0 + 13.0 * v ** 1.45                   # gęściej przy kamerze
        X, Y = np.meshgrid(x, y)
        dx = 14.0 / nx; dy = np.gradient(y)[:, None] * np.ones((1, nx))
        self.X = (X + (r.random(X.shape) - 0.5) * dx).astype(np.float32)
        self.Y = (Y + (r.random(X.shape) - 0.5) * dy).astype(np.float32)
        self.dx, self.dy = np.float32(dx), dy.astype(np.float32)
        self.jas = (0.35 + 1.0 * r.random(X.shape) ** 2.2).astype(np.float32)    # jasność ziarna
        mix = r.random(X.shape).astype(np.float32)
        mix2 = r.random(X.shape).astype(np.float32)
        self.kol = (SZAMPAN * (1 - mix)[..., None] + MIEDZ * mix[..., None]) * (1 - 0.35 * mix2[..., None]) \
            + ROZ * (0.35 * mix2[..., None])
        # mikrościanki: losowe odchylenie normalnej + faza i prędkość obrotu
        self.fa = (r.random(X.shape) * 6.283).astype(np.float32)
        self.fs = (0.4 + 1.6 * r.random(X.shape)).astype(np.float32)
        self.fo = (r.random(X.shape) * 6.283).astype(np.float32)
        # miejsca półtonów: wysokość → x (lewo nisko, prawo wysoko), klasa wysokości → głębokość
        self.nuty_xy = []
        for k in range(M1 - M0):
            mm = M0 + k
            nx_ = -3.9 + 7.8 * k / (M1 - M0 - 1)
            ny_ = 0.5 + 3.4 * ((mm * 7) % 12) / 11.0      # krąg kwintowy rozrzuca sąsiednie półtony
            self.nuty_xy.append((nx_, ny_))
        self.wiry = [(-1.6, 2.4, 1.7, 1), (1.8, 3.4, 2.0, -1), (0.1, 6.2, 2.6, 1), (-3.6, 5.6, 1.9, -1), (3.7, 1.4, 1.3, 1)]
        self.fale = [(r.uniform(0, 6.28), r.uniform(0.3, 0.8), r.uniform(0, 6.28)) for _ in range(5)]


def kamera(t, dl):
    """Nisko nad piaskiem, powolny najazd i lekki obrót (głębia, paralaksa)."""
    s = t / max(dl, 1e-6)
    e = s * s * (3 - 2 * s)
    az = math.radians(-7 + 12 * e)
    odl = 5.6 - 0.8 * e
    cel = np.array([0.0, 3.1, -0.1])
    pos = cel + np.array([odl * math.sin(az), -odl * math.cos(az), 2.55 + 0.12 * math.sin(2.1 * t)])
    return Kamera(pos, cel, ogniskowa=1.22)


# ----------------------------------------------------------------------------- wysokość
def _okno(sw, cx, cy, R):
    """Wycinek siatki wokół (cx, cy) o promieniu R – lokalne liczenie wybrzuszeń."""
    j0 = int(np.clip((cx - R + 7.0) / 14.0 * sw.nx, 0, sw.nx)); j1 = int(np.clip((cx + R + 7.0) / 14.0 * sw.nx, 0, sw.nx))
    yr = sw.Y[:, sw.nx // 2]
    i0 = int(np.searchsorted(yr, cy - R)); i1 = int(np.searchsorted(yr, cy + R))
    return slice(i0, i1), slice(j0, j1)


def wysokosc(sw, p, k):
    t = p["t"][k]; L, M, Hh = p["L"][k], p["M"][k], p["H"][k]
    X, Y = sw.X, sw.Y
    wx = np.zeros_like(X); wy = np.zeros_like(X)
    for a, kk, f0 in sw.fale:
        arg = kk * (X * math.cos(a) + Y * math.sin(a)) + f0 + 0.3 * p["fL"][k]
        wx += 0.3 * np.sin(arg); wy += 0.3 * np.cos(1.3 * arg + 1)
    Xw, Yw = X + wx, Y + wy
    # wydmy tła (spokojnie)
    h = 0.10 * np.sin(0.6 * Xw + 0.45 * Yw - 0.5 * p["fL"][k]) + 0.07 * np.sin(0.37 * Xw - 0.8 * Yw + 1.3)
    # bas → doliny i leje (ujemne), wysokie → wzgórza (dodatnie), wielkoskalowo
    pole = np.sin(0.85 * Xw + 0.3 * np.sin(0.7 * Yw)) * np.sin(0.75 * Yw - 0.4 * Xw + 0.3 * p["fL"][k])
    h += -0.55 * L * np.clip(-pole, 0, None) ** 1.3
    szczyty = np.clip(pole, 0, None) ** 1.6 * (0.6 + 0.4 * np.sin(2.3 * Xw - 1.7 * Yw + p["fH"][k] * 0.6))
    h += 0.75 * Hh * szczyty
    # wiry: spiralne grzbiety (średnie) i leje w środku (bas)
    for cx, cy, R, kier in sw.wiry:
        dx_, dy_ = Xw - cx, (Yw - cy) * 1.15
        r2 = dx_ * dx_ + dy_ * dy_
        rr = np.sqrt(r2) + 1e-4
        spir = (0.5 + 0.5 * np.sin(2 * np.pi * rr / (R * 0.11) + kier * 2 * np.arctan2(dy_, dx_) - 2.5 * p["fM"][k])) ** 4
        ot = np.exp(-r2 / (R * R))
        h += (0.03 + 0.10 * M) * spir * ot - (0.06 + 0.35 * L) * np.exp(-r2 / (R * R * 0.12))
    # każdy półton: wybrzuszenie w górę (wysokie) / w dół (niskie) z koncentryczną zmarszczką
    nuty = p["nuty"][k]
    for b in np.nonzero(nuty > 0.04)[0]:
        a = float(nuty[b]); cx, cy = sw.nuty_xy[b]
        znak = math.tanh(((M0 + b) - 64) / 7.0)           # E4 jako granica: wyżej ↑, niżej ↓
        R = 0.55 + 0.35 * (1 - (b / (M1 - M0)))
        sy, sx = _okno(sw, cx, cy, R * 2.2)
        if sy.start >= sy.stop or sx.start >= sx.stop:
            continue
        dx_, dy_ = Xw[sy, sx] - cx, Yw[sy, sx] - cy
        r2 = dx_ * dx_ + dy_ * dy_
        g = np.exp(-r2 / (R * R))
        zm = 0.75 + 0.25 * np.cos(np.sqrt(r2) * 9.0 - 6.0 * t)
        h[sy, sx] += (0.85 if znak > 0 else 0.6) * znak * a * g * zm
    # ataki: pierścień-fala od środka sceny
    for j, (ta, sila) in enumerate(p["ataki"]):
        dt = t - ta
        if 0 <= dt < 2.0:
            cx, cy = sw.wiry[j % 3][:2]
            rr = np.hypot(Xw - cx, Yw - cy)
            h += 0.22 * (0.4 + 0.6 * sila) * np.exp(-((rr - (0.3 + 3.2 * dt)) / 0.22) ** 2) * math.exp(-dt / 0.7)
    # drobne zmarszczki (wysokie)
    h += (0.004 + 0.012 * Hh) * np.sin(38 * (Xw * 0.8 + Yw * 0.6) + 2.5 * np.sin(1.2 * Yw) - p["fH"][k])
    return (h * AMPLITUDA).astype(np.float32)


# ----------------------------------------------------------------------------- render
def _splat_z(sx, sy, z, C, glebia_ostr, warstwy=3, rozm=0.42):
    """Rzut ziaren z buforem głębokości (bliższe zasłaniają dalsze) i głębią ostrości."""
    ix = np.round(sx).astype(np.int64); iy = np.round(sy).astype(np.int64)
    idx = iy * W + ix
    zb = np.full(H * W, np.inf, np.float32)
    np.minimum.at(zb, idx, z)
    zb = cv2.erode(zb.reshape(H, W), np.ones((3, 3), np.uint8)).ravel()     # zasłanianie także przez szczeliny
    widac = z <= zb[idx] * 1.012 + 0.004
    sx, sy, z, C = sx[widac], sy[widac], z[widac], C[widac]
    rozmycie = np.abs(np.log(z / glebia_ostr))
    kraw = np.quantile(rozmycie, np.linspace(0, 1, warstwy + 1))
    out = np.zeros((H, W, 3), np.float32)
    for q in range(warstwy):
        m = (rozmycie >= kraw[q]) & (rozmycie <= kraw[q + 1] + 1e-9)
        x, y, c = sx[m], sy[m], C[m]
        x0 = np.floor(x).astype(np.int64); y0 = np.floor(y).astype(np.int64)
        fx = (x - x0).astype(np.float32); fy = (y - y0).astype(np.float32)
        acc = np.zeros((3, H * W), np.float64)
        for ddx, ddy, w in ((0, 0, (1 - fx) * (1 - fy)), (1, 0, fx * (1 - fy)), (0, 1, (1 - fx) * fy), (1, 1, fx * fy)):
            ii = (y0 + ddy) * W + (x0 + ddx)
            for ch in range(3):
                acc[ch] += np.bincount(ii, weights=c[:, ch] * w, minlength=H * W)
        lay = acc.reshape(3, H, W).transpose(1, 2, 0).astype(np.float32)
        sig = rozm * (kraw[q] + kraw[q + 1]) / 2 * 6
        if sig > 0.35:
            lay = cv2.GaussianBlur(lay, (0, 0), sig)
        out += lay
    return out


def klatka(sw, p, k):
    t = p["t"][k]; L, Hh, E = p["L"][k], p["H"][k], p["E"][k]
    h = wysokosc(sw, p, k)
    gy, gx = np.gradient(h)
    hx = gx / sw.dx; hy = gy / sw.dy
    nz = 1 / np.sqrt(1 + hx * hx + hy * hy)
    n = np.stack([-hx * nz, -hy * nz, nz], -1)
    kam = kamera(t, p["dl"])
    P = np.stack([sw.X, sw.Y, h], -1).reshape(-1, 3)
    nn = n.reshape(-1, 3)
    sx, sy, z = kam.rzut(P)
    ok = (sx >= 0) & (sx < W - 1) & (sy >= 0) & (sy < H - 1) & (z > 0.1)
    # światło: rozproszone pod małym kątem + kontra
    dif = np.clip(nn @ SWIATLO, 0, None)
    v = kam.pos[None, :] - P
    v /= np.linalg.norm(v, axis=1, keepdims=True)
    hv = SWIATLO[None, :] + v; hv /= np.linalg.norm(hv, axis=1, keepdims=True)
    # mikrościanki ziaren: odchylona normalna, powoli obracana (mienienie się)
    ob = sw.fa.ravel() + t * sw.fs.ravel() * (0.6 + 2.2 * Hh + 1.2 * E)
    nf = nn + 0.45 * np.stack([np.cos(ob) * np.cos(sw.fo.ravel()), np.sin(ob) * np.cos(sw.fo.ravel()),
                               0.3 * np.sin(sw.fo.ravel())], 1)
    nf /= np.linalg.norm(nf, axis=1, keepdims=True)
    blysk = np.clip(np.sum(nf * hv, 1), 0, 1) ** 60 * (0.25 + 1.4 * Hh + 0.8 * E)
    swiatlo = (0.06 + 1.25 * dif ** 1.4)
    # barwa wg wysokości: dodatnia (wysokie tony) → pomarańcz, ujemna (bas) → błękit
    hz = h.ravel()
    w_pom = np.clip(hz / 0.22, 0, 1) ** 1.1
    w_nieb = np.clip(-hz / 0.20, 0, 1) ** 1.1
    kol = sw.kol.reshape(-1, 3)
    kol = kol * (1 - 0.9 * w_pom - 0.9 * w_nieb)[:, None] + POMARANCZ * (0.95 * w_pom)[:, None] \
        + NIEBIESKI * (0.95 * w_nieb)[:, None]
    jas = sw.jas.ravel()
    C = kol * (swiatlo * jas)[:, None] + (kol * 0.4 + 0.6) * blysk[:, None] * 2.2
    # spadek gęstości: dalsze ziarna rzutują się gęściej – kompensata wagi
    C *= np.clip(z / kam.ostrosc, 0.3, 3.0)[:, None] ** -0.35 * 0.62
    # wygaszenie brzegów pola (żadnej widocznej krawędzi)
    kx = np.clip((7.0 - np.abs(sw.X.ravel())) / 2.0, 0, 1); ky = np.clip((11.0 - sw.Y.ravel()) / 3.0, 0, 1)
    C *= (kx * kx * ky * ky)[:, None]
    C = C.astype(np.float32)
    em = _splat_z(sx[ok], sy[ok], z[ok], C[ok], kam.ostrosc * 0.92)
    return em


def wywolaj(em, sw=None):
    yy = np.linspace(0, 1, H)[:, None, None]
    tlo = TLO_GORA * (1 - yy) + TLO_DOL * yy
    q = cv2.resize(em, (W // 4, H // 4), interpolation=cv2.INTER_AREA)
    bl = cv2.resize(0.6 * cv2.GaussianBlur(q, (0, 0), 3) + 0.3 * cv2.GaussianBlur(q, (0, 0), 12), (W, H))
    img = 1 - np.exp(-(em * 1.45 + 0.32 * bl))
    out = 1 - (1 - tlo) * (1 - img)
    yy2, xx2 = np.mgrid[0:H, 0:W].astype(np.float32)
    win = 1 - 0.35 * (((xx2 / W - 0.5) * 1.1) ** 2 + ((yy2 / H - 0.55) * 1.3) ** 2)
    out = out * win[..., None]
    out = cv2.resize(out.astype(np.float32), (W_OUT, H_OUT), interpolation=cv2.INTER_AREA)
    return (np.clip(out, 0, 1) * 255 + 0.5).astype(np.uint8)
