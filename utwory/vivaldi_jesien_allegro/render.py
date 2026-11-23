"""CHOPIN — Matematyka muzyki. Walc a-moll B.150 – animacja neonowa 3D sterowana plikiem MIDI.

Scena: klawiatura fortepianu na pierwszym planie, przed nią wijący się neonowy tor, po którym toczą się
szklane kule nut (tor = oś czasu, pas = klawisz, rozmiar = głośność, świetlisty ślad = długość nuty).
W tle świecące koło kwintowe (dur na zewnątrz, moll wewnątrz): segmenty rozświetlają się z melodią
i harmonią, w środku melodia rysuje cięciwy, a akord – wielokąt. Po bokach z każdego taktu wyrasta
szklany sześcian (wysokość = średnia wysokość melodii w takcie, kolor = funkcja harmonii).
Napisy edukacyjne pojawiają się tylko wtedy, gdy w muzyce dzieje się to, co opisują.

  RES=1 python render_neon.py --test 10 30      (RES=1 → 1920×1080, RES=2 → 3840×2160)
  RES=2 python render_neon.py --seg 0 800 seg0.mp4
"""
import argparse
import math
import os
import subprocess
from multiprocessing import Pool

import cv2
import numpy as np
from PIL import Image, ImageDraw, ImageFont

import sys as _sys
from pathlib import Path as _Path
ROOT = _Path(__file__).resolve().parents[2]
_sys.path.insert(0, str(ROOT / "wspolne"))
from midi_io import read_midi_full

cv2.setNumThreads(1)
HERE = os.path.dirname(os.path.abspath(__file__))
MIDI = os.environ.get("MIDI", os.path.join(HERE, "autumn_piano.mid"))
S = float(os.environ.get("RES", "1"))
W, H, FPS = int(1920 * S), int(1080 * S), 30
DUR = float(os.environ.get("DUR", "308.0"))
NF = int(round(DUR * FPS))
FONT_SERIF_I = str(ROOT / "assets/fonts/FreeSerifItalic.ttf")
FONT_SERIF = str(ROOT / "assets/fonts/FreeSerif.ttf")
FONT_L = str(ROOT / "assets/fonts/Inter-Light.otf")
FONT_M = str(ROOT / "assets/fonts/Inter-Medium.otf")
FONT_SB = str(ROOT / "assets/fonts/Inter-SemiBold.otf")


def hexc(h):
    return np.array([int(h[i:i + 2], 16) / 255 for i in (1, 3, 5)], np.float32)


def sst(a, b, x):
    u = np.clip((np.asarray(x, float) - a) / (b - a), 0, 1)
    return u * u * (3 - 2 * u)


def fs(a, b, x):
    return float(sst(a, b, x))


# kolory w kolejności koła kwintowego: C G D A E H Fis Cis Gis Dis B F
FCOL = [hexc(h) for h in ("#FF8C1A", "#FFC21A", "#E8D83A", "#A6CF3A", "#4FB86B", "#2EA894",
                          "#3A86C8", "#6A5ACD", "#A8409A", "#D8304F", "#E8482A", "#FF6A22")]
NNAME = ["C", "Cis", "D", "Dis", "E", "F", "Fis", "G", "Gis", "A", "B", "H"]
MAJ = ["C", "G", "D", "A", "E", "H", "Fis", "Des", "As", "Es", "B", "F"]
MIN = ["a", "e", "h", "fis", "cis", "gis", "es", "b", "f", "c", "g", "d"]
GOLD = hexc("#FFC23A"); PINK = hexc("#E8482A"); VIOLET = hexc("#C2611D"); CYAN = hexc("#F2A541")
WHITE = np.ones(3, np.float32)


def fifth(pc):
    return (int(pc) * 7) % 12


def pcol(pc):
    return FCOL[fifth(pc)]


# ----------------------------------------------------------------------------- dane MIDI
NOTES, PPQ, MARKS = read_midi_full(MIDI)
MEL = [x for x in NOTES if x["ch"] == 0]
ACC = [x for x in NOTES if x["ch"] == 1]
mt0 = np.array([x["t0"] for x in MEL]); mt1 = np.array([x["t1"] for x in MEL])
mp = np.array([x["pitch"] for x in MEL]); mv = np.array([x["vel"] for x in MEL], float)
mk0 = np.array([x["k0"] for x in MEL])
NM = len(MEL); mpc = mp % 12
at0 = np.array([x["t0"] for x in ACC]); at1 = np.array([x["t1"] for x in ACC])
ap = np.array([x["pitch"] for x in ACC]); av = np.array([x["vel"] for x in ACC], float)
_groups = {}
for x in ACC:
    _groups.setdefault(x["k0"], []).append(x)
AEV = []
for k0 in sorted(_groups):
    g = _groups[k0]; beat = (k0 // PPQ) % 4; low = min(x["pitch"] for x in g)
    if k0 % PPQ == 0:
        AEV.append((g[0]["t0"], beat, sorted({x["pitch"] % 12 for x in g}), beat == 0, low % 12, k0))
ae_t = np.array([e[0] for e in AEV])
BT = 4 * PPQ
_tk = {}
for x in NOTES:
    _tk.setdefault(x["k0"], x["t0"])
HARM = []
for bar in sorted({x["k0"] // BT for x in NOTES}):
    ks = bar * BT
    if ks not in _tk:
        continue
    sound = [x for x in ACC if x["k0"] <= ks < x["k1"]]
    inbar = [x for x in ACC if ks <= x["k0"] < ks + BT and x["k0"] % PPQ == 0]
    if not sound:
        continue
    root = min(sound, key=lambda x: x["pitch"])["pitch"] % 12
    pcs = sorted({x["pitch"] % 12 for x in sound + inbar}, key=fifth)
    HARM.append((_tk[ks], root, pcs, ks))
h_t = np.array([h[0] for h in HARM])
SEC = [(m[1], m[2]) for m in MARKS]
T_END = float(max(x["t1"] for x in NOTES))
all_t0 = np.array([x["t0"] for x in NOTES]); all_v = np.array([x["vel"] for x in NOTES], float)

def key_mode(t):
    lab = "A"
    for ts, l in SEC:
        if t >= ts - 0.05:
            lab = l[0]
    return "dur"


# ----------------------------------------------------------------------------- kamera i geometria 3D
F = 900 * S
XC, YH = W / 2, 600 * S
HC = 0.95
LOWK, HIGHK = 36, 91


def is_black(p):
    return (p % 12) in (1, 3, 6, 8, 10)


_whites = [p for p in range(LOWK, HIGHK + 1) if not is_black(p)]
KW = 5.95 / len(_whites)
_wpos = {p: i for i, p in enumerate(_whites)}
XOFF = -(len(_whites) - 1) / 2 * KW + 0.0


def key_x(p):
    p = int(p)
    if not is_black(p):
        return XOFF + _wpos[p] * KW
    return XOFF + _wpos[p - 1] * KW + KW / 2


Z_FRONT, Z_HIT = 2.75, 2.85
VZ = 3.1                      # jednostek / s (prędkość nadjeżdżania nut)
Z_FAR = Z_HIT + VZ * 4.2


def curve(z, t):
    z = np.asarray(z, float)
    return 0.95 * np.sin(0.21 * (z - Z_HIT) + 0.30 * t) * sst(5.5, 12.0, z) \
        + 0.35 * np.sin(0.5 * t) * sst(4.0, 9.0, z)


def proj(x, y, z):
    z = np.maximum(np.asarray(z, float), 0.05)
    return XC + F * np.asarray(x, float) / z, YH + F * (HC - np.asarray(y, float)) / z


# koło kwintowe
WCX, WCY = 960 * S, 330 * S
R_O, R_M, R_I = 318 * S, 222 * S, 150 * S


def wheel_pt(pc, r):
    a = math.radians(-90 + 30 * fifth(pc))
    return WCX + r * math.cos(a), WCY + r * math.sin(a)


# ----------------------------------------------------------------------------- tekst
def text_sprite(txt, font, size, col=(1, 1, 1), spacing=0, sup=None):
    f = ImageFont.truetype(font, int(size * S))
    chars = list(txt)
    wsum = sum(f.getlength(c) for c in chars) + spacing * S * max(0, len(chars) - 1)
    fsup = ImageFont.truetype(font, int(size * S * 0.58)) if sup else None
    wsup = fsup.getlength(sup) + 4 * S if sup else 0
    asc, desc = f.getmetrics()
    im = Image.new("L", (int(wsum + wsup + 12 * S), int(asc + desc + 12 * S)), 0)
    d = ImageDraw.Draw(im)
    x = 6 * S
    for c in chars:
        d.text((x, 6 * S), c, font=f, fill=255)
        x += f.getlength(c) + spacing * S
    if sup:
        d.text((x + 2 * S, 6 * S - size * S * 0.12), sup, font=fsup, fill=255)
    a = np.asarray(im, np.float32) / 255
    return a, np.asarray(col, np.float32)


def blit(img, spr, x, y, alpha=1.0, grad=None):
    a, col = spr
    h, w = a.shape
    x, y = int(x), int(y)
    x0, y0 = max(0, x), max(0, y); x1, y1 = min(W, x + w), min(H, y + h)
    if x1 <= x0 or y1 <= y0 or alpha <= 0.003:
        return
    aa = a[y0 - y:y1 - y, x0 - x:x1 - x][..., None] * alpha
    c = col if grad is None else grad[y0 - y:y1 - y, x0 - x:x1 - x]
    roi = img[y0:y1, x0:x1]
    roi[:] = roi * (1 - aa) + c * aa


# ----------------------------------------------------------------------------- prymitywy
LD = np.array([-0.45, -0.62, 0.64], np.float32); LD /= np.linalg.norm(LD)


def draw_ball(img, em, cx, cy, r, col, alpha=1.0, glow=0.5):
    if r < 0.8 or alpha <= 0.004:
        return
    x0 = max(0, int(cx - r * 2.2)); x1 = min(W, int(cx + r * 2.2) + 2)
    y0 = max(0, int(cy - r * 2.2)); y1 = min(H, int(cy + r * 2.6) + 2)
    if x1 <= x0 or y1 <= y0:
        return
    xs = np.arange(x0, x1, dtype=np.float32)[None, :] + 0.5
    ys = np.arange(y0, y1, dtype=np.float32)[:, None] + 0.5
    dx = (xs - cx) / r; dy = (ys - cy) / r
    d = np.sqrt(dx * dx + dy * dy)
    col = np.asarray(col, np.float32)
    if glow > 0:
        g = glow * alpha * np.exp(-np.maximum(d - 0.9, 0) * 2.4) * 0.5
        em[y0:y1, x0:x1] += g[..., None] * col
    # cień/odbicie pod kulą
    sh = np.exp(-(((xs - cx) / (1.1 * r)) ** 2 + ((ys - cy - 0.95 * r) / (0.28 * r)) ** 2))
    roi = img[y0:y1, x0:x1]
    roi *= (1 - 0.5 * alpha * sh)[..., None]
    a = np.clip((1 - d) * r + 0.5, 0, 1) * alpha
    nz = np.sqrt(np.clip(1 - d * d, 0, 1))
    diff = np.clip(dx * LD[0] + dy * LD[1] + nz * LD[2], 0, 1)
    core = np.exp(-((dx - 0.15) ** 2 + (dy - 0.25) ** 2) / 0.35)
    fres = (1 - nz) ** 2.5
    rgb = col * (0.25 + 0.55 * diff[..., None] + 0.65 * core[..., None])
    rgb = rgb + fres[..., None] * (0.55 * col + 0.25)
    spec = 1.1 * np.exp(-((dx + 0.38) ** 2 + (dy + 0.42) ** 2) / (2 * 0.09 ** 2)) \
        + 0.30 * np.exp(-((dx - 0.25) ** 2 + (dy - 0.62) ** 2) / (2 * 0.12 ** 2))
    rgb = rgb + spec[..., None]
    roi[:] = roi * (1 - a[..., None]) + rgb * a[..., None]


class Layer:
    """warstwa uint8 do rysowania kształtów cv2 (dodawana jako emisja lub mieszana z alfą)."""

    def __init__(self):
        self.c = np.zeros((H, W, 3), np.uint8)
        self.used = False

    def P(self, pts):
        return np.round(np.asarray(pts, float) * 16).astype(np.int32).reshape(-1, 1, 2)

    def col(self, c, a):
        return tuple(int(min(1.0, max(0.0, v * a)) * 255) for v in c)

    def lines(self, pts, c, a, th, closed=False):
        if a > 0.004:
            cv2.polylines(self.c, [self.P(pts)], closed, self.col(c, a), max(1, int(round(th * S))), cv2.LINE_AA, 4)
            self.used = True

    def poly(self, pts, c, a):
        if a > 0.004:
            cv2.fillPoly(self.c, [self.P(pts)], self.col(c, a), cv2.LINE_AA, 4)
            self.used = True

    def circle(self, x, y, r, c, a, th=-1):
        if a > 0.004 and r > 0:
            cv2.circle(self.c, (int(x * 16), int(y * 16)), int(r * 16), self.col(c, a),
                       -1 if th < 0 else max(1, int(round(th * S))), cv2.LINE_AA, 4)
            self.used = True


# ----------------------------------------------------------------------------- statyczne tło
def build_static():
    yy, xx = np.mgrid[0:H, 0:W].astype(np.float32)
    yy /= H; xx /= W
    sky = hexc("#0C0A1E") * (1 - yy[..., None]) + hexc("#3E1622") * yy[..., None]
    # mgławice
    rng = np.random.default_rng(3)
    for (cx, cy, r, c, k) in ((0.15, 0.25, 0.35, VIOLET, 0.30), (0.85, 0.35, 0.30, CYAN, 0.18),
                              (0.5, 0.52, 0.45, GOLD, 0.18), (0.75, 0.10, 0.25, hexc("#5A2A8A"), 0.20)):
        g = np.exp(-(((xx - cx) * 1.78) ** 2 + (yy - cy) ** 2) / (r * r))
        sky = sky + (g * k)[..., None] * c * 0.6
    img = sky.astype(np.float32)
    # gwiazdy
    n = int(900 * S)
    sx = rng.random(n) * W; sy = rng.random(n) * YH * 0.98
    sb = rng.random(n) ** 3 * 0.9 + 0.08
    for x, y, b in zip(sx, sy, sb):
        r = 0.6 * S + 1.2 * S * b
        cv2.circle(img, (int(x * 16), int(y * 16)), int(r * 16), (b * .9, b * .9, b), -1, cv2.LINE_AA, 4)
    # podłoga (odbijająca, ciemna) z subtelną siatką perspektywiczną
    fl = np.clip((yy * H - YH) / (H - YH), 0, 1)[..., None]
    floor = hexc("#2E1410") * (1 - fl) + hexc("#0A0505") * fl
    m = (yy * H >= YH)[..., None]
    img = np.where(m, floor, img).astype(np.float32)
    hz = np.exp(-((yy * H - YH) / (14 * S)) ** 2)[..., None]
    img += hz * (0.55 * VIOLET + 0.30 * GOLD) * 0.6
    grid = np.zeros((H, W, 3), np.uint8)
    for z in np.arange(4.0, 40, 1.5):
        y = YH + F * HC / z
        cv2.line(grid, (0, int(y * 16)), (W * 16, int(y * 16)), (150, 75, 35), max(1, int(S)), cv2.LINE_AA, 4)
    for x in np.arange(-30, 31, 1.5):
        p0 = proj(x, 0, 2.0); p1 = proj(x, 0, 60.0)
        cv2.line(grid, (int(p0[0] * 16), int(p0[1] * 16)), (int(p1[0] * 16), int(p1[1] * 16)), (150, 75, 35),
                 max(1, int(S)), cv2.LINE_AA, 4)
    gf = grid.astype(np.float32) / 255 * 0.35 * np.clip((yy * H - YH) / (60 * S), 0, 1)[..., None]
    img += gf
    # klawiatura (statyczna)
    draw_keyboard(img, None)
    return img.astype(np.float32)


YK0, YK1, YKB = 904 * S, 1076 * S, 1012 * S
PXU = F / Z_HIT


def kx(p):
    return XC + PXU * key_x(p)


def key_quad(p, depress=0.0):
    x = kx(p); dy = 3 * S * depress
    if is_black(p):
        w = KW * PXU * 0.30
        return np.array([(x - w, YK0 - 2 * S + dy), (x + w, YK0 - 2 * S + dy), (x + w, YKB + dy), (x - w, YKB + dy)])
    w = KW * PXU * 0.47
    return np.array([(x - w, YK0 + dy), (x + w, YK0 + dy), (x + w, YK1 + dy), (x - w, YK1 + dy)])


def fill(img, pts, col, a=1.0):
    m = np.zeros(img.shape[:2], np.uint8)
    x0, y0 = np.floor(pts.min(0)).astype(int) - 2; x1, y1 = np.ceil(pts.max(0)).astype(int) + 2
    x0, y0 = max(x0, 0), max(y0, 0); x1, y1 = min(x1, W), min(y1, H)
    if x1 <= x0 or y1 <= y0:
        return
    mm = np.zeros((y1 - y0, x1 - x0), np.uint8)
    cv2.fillPoly(mm, [np.round((pts - [x0, y0]) * 16).astype(np.int32).reshape(-1, 1, 2)], 255, cv2.LINE_AA, 4)
    aa = mm.astype(np.float32)[..., None] / 255 * a
    roi = img[y0:y1, x0:x1]
    c = np.asarray(col, np.float32)
    if c.ndim == 1:
        roi[:] = roi * (1 - aa) + c * aa
    else:
        roi[:] = roi * (1 - aa) + c[y0:y1, x0:x1] * aa


def draw_keyboard(img, lit):
    if lit is None:
        fill(img, np.array([(0, YK0 - 10 * S), (W, YK0 - 10 * S), (W, H), (0, H)]), hexc("#140806"))
        fill(img, np.array([(0, YK0 - 8 * S), (W, YK0 - 8 * S), (W, YK0 - 2 * S), (0, YK0 - 2 * S)]), hexc("#8B1A1A"))
    ys = np.linspace(0, 1, int(YK1 - YK0) + 2, dtype=np.float32)
    for black in (False, True):
        for p in range(LOWK, HIGHK + 1):
            if is_black(p) != black:
                continue
            Lv = 0.0 if lit is None else lit.get(p, 0.0)
            if lit is not None and Lv <= 0.01 and not black:
                continue
            q = key_quad(p, Lv)
            if black:
                ct = hexc("#15110B")
            else:
                ct = hexc("#F4ECD8")
            if Lv > 0:
                c = lit_col[p]
                ct = c * (0.75 + 0.25 * Lv) + 0.18 * Lv if not black else c * (0.55 + 0.45 * Lv)
            fill(img, q, ct)
            x0, y0 = q[0]; x1, y1 = q[2]
            if not black:
                fill(img, np.array([(x0, y1 - 10 * S), (x1, y1 - 10 * S), (x1, y1), (x0, y1)]), ct * 0.72)
                fill(img, np.array([(x0, y0), (x1, y0), (x1, y0 + 30 * S), (x0, y0 + 30 * S)]), np.zeros(3), 0.18)
            else:
                fill(img, np.array([(x0 + 3 * S, y0 + 4 * S), (x0 + 7 * S, y0 + 4 * S), (x0 + 7 * S, y1 - 12 * S), (x0 + 3 * S, y1 - 12 * S)]), WHITE, 0.22)
                fill(img, np.array([(x0, y1 - 9 * S), (x1, y1 - 9 * S), (x1, y1), (x0, y1)]), ct * 0.55 + 0.05)


lit_col = {}


# ----------------------------------------------------------------------------- koło kwintowe (mapy)
def build_wheel():
    x0, y0 = int(WCX - R_O - 8 * S), int(WCY - R_O - 8 * S)
    x1, y1 = int(WCX + R_O + 8 * S), int(WCY + R_O + 8 * S)
    yy, xx = np.mgrid[y0:y1, x0:x1].astype(np.float32) + 0.5
    dx, dy = xx - WCX, yy - WCY
    r = np.sqrt(dx * dx + dy * dy)
    a = (np.degrees(np.arctan2(dy, dx)) + 90 + 15) % 360
    k = (a // 30).astype(np.int32)
    idx = np.where(r < R_M, k + 12, k)
    idx = np.where(r < R_I, 24, idx)
    aa = np.clip(R_O - r + 0.5, 0, 1)
    rad = np.clip((r - R_I) / (R_O - R_I), 0, 1)
    # cieniowanie segmentu (pseudo-3D): jaśniej przy zewnętrznej krawędzi każdego pierścienia
    ring_u = np.where(r >= R_M, (r - R_M) / (R_O - R_M), (r - R_I) / (R_M - R_I))
    shade = 0.62 + 0.38 * np.clip(ring_u, 0, 1)
    # linie podziału i okręgi (statyczne, emisyjne)
    lay = np.zeros((y1 - y0, x1 - x0, 3), np.uint8)
    c16 = lambda x, y: (int((x - x0) * 16), int((y - y0) * 16))
    for kk in range(12):
        ang = math.radians(-90 + 30 * kk - 15)
        p0 = (WCX + R_I * math.cos(ang), WCY + R_I * math.sin(ang))
        p1 = (WCX + R_O * math.cos(ang), WCY + R_O * math.sin(ang))
        cv2.line(lay, c16(*p0), c16(*p1), (150, 150, 200), max(1, int(1.5 * S)), cv2.LINE_AA, 4)
    for rr, c in ((R_O, (255, 220, 150)), (R_M, (160, 150, 220)), (R_I, (200, 170, 255))):
        cv2.circle(lay, c16(WCX, WCY), int(rr * 16), c, max(1, int(2 * S)), cv2.LINE_AA, 4)
    # napisy
    lab = np.zeros((y1 - y0, x1 - x0), np.float32)
    for kk in range(12):
        for txt, rr, size, font in ((MAJ[kk], (R_M + R_O) / 2, 52, FONT_SB), (MIN[kk], (R_I + R_M) / 2, 30, FONT_M)):
            a_, _ = text_sprite(txt, font, size)
            ang = math.radians(-90 + 30 * kk)
            cx, cy = WCX + rr * math.cos(ang) - x0, WCY + rr * math.sin(ang) - y0
            h, w = a_.shape
            ys, xs = int(cy - h / 2 - 3 * S), int(cx - w / 2)
            lab[ys:ys + h, xs:xs + w] = np.maximum(lab[ys:ys + h, xs:xs + w], a_)
    # klucz wiolinowy w środku
    f = ImageFont.truetype(FONT_SERIF, int(200 * S))
    im = Image.new("L", (int(260 * S), int(340 * S)), 0)
    ImageDraw.Draw(im).text((int(50 * S), int(30 * S)), "\U0001D11E", font=f, fill=255)
    cl = np.asarray(im, np.float32) / 255
    ys_, xs_ = np.nonzero(cl > 0.05)
    cl = cl[ys_.min():ys_.max() + 1, xs_.min():xs_.max() + 1]
    h, w = cl.shape
    ys, xs = int(WCY - y0 - h / 2), int(WCX - x0 - w / 2)
    clef = np.zeros_like(lab); clef[ys:ys + h, xs:xs + w] = cl
    return dict(box=(x0, y0, x1, y1), idx=idx, aa=aa, shade=shade, rad=rad, lines=lay.astype(np.float32) / 255,
                lab=lab, clef=clef, r=r)


# ----------------------------------------------------------------------------- napisy edukacyjne
# lokalne tempo z uderzeń basu (każda miara ma uderzenie akompaniamentu)
_bt = np.array(sorted({e[0] for e in AEV}))
_ibi = np.diff(_bt)
BPM_MED = 60 / float(np.median(_ibi))


def build_captions():
    caps, used = [], [(0, 5.4)]

    def free(t, d):
        return all(t + d + 0.8 < a or t > b + 0.8 for a, b in used)

    def add(t, d, a, b, sup=None):
        if free(t, d):
            caps.append((t, d, a, b, sup)); used.append((t, t + d))

    add(6.0, 4.8, "Allegro · metrum 4/4", "tempo ≈ %d uderzeń na minutę – zmierzone z nagrania" % round(BPM_MED))
    add(13.0, 4.8, "Nuty odczytane z nagrania skrzypiec", "transformata Fouriera rozkłada dźwięk na częstotliwości")
    add(21.0, 4.8, "Spirala częstotliwości", "jeden obrót = oktawa: częstotliwość rośnie dokładnie × 2")
    add(TREE_FULL + 0.2, 4.8, "Drzewo fraktalne", "każda gałąź dzieli się na dwie: 2⁹ = 512 gałązek")
    # wolniejszy epizod: lokalne tempo < 75% mediany przez dłuższy czas
    loc = uniform = np.convolve(_ibi, np.ones(6) / 6, mode="same")
    slow = np.nonzero(60 / loc < 0.75 * BPM_MED)[0]
    if len(slow):
        add(float(_bt[slow[0]]), 5.0, "Wolniejszy epizod", "muzyka zwalnia – jesienne „zaśnięcie” po zabawie")
    add(T_END * 0.5, 4.8, "Liście = nuty melodii", "każda nuta zapala liść, który potem opada z drzewa")
    add(T_END * 0.80, 4.8, "Częstotliwość nuty", "f = 440 · 2", "n/12")
    caps.sort()
    return caps, []




# ----------------------------------------------------------------------------- drzewo fraktalne i spirala częstotliwości
TR_X, TR_Y, TR_L0, TR_RAT = 300 * S, 520 * S, 112 * S, 0.72
TREE_MAX = 9
TREE_FULL = 30.0          # sekunda, w której drzewo osiąga pełną głębokość


def tree_depth(t):
    return float(np.clip(1 + (TREE_MAX - 1) * (t - 1.0) / (TREE_FULL - 1.0), 0, TREE_MAX))


def tree_geom(t, en):
    """lista gałęzi (x0,y0,x1,y1,poziom) oraz końcówek (dla liści)."""
    depth = tree_depth(t)
    hi = max(0, harm_at_idx(t))
    minor = 0
    spread = math.radians(24 + 6 * math.sin(0.11 * t))
    segs, tips = [], []
    stack = [(TR_X, TR_Y, -math.pi / 2, TR_L0, 0, 0)]
    while stack:
        x, y, a, L, d, code = stack.pop()
        grow = float(np.clip(depth - d, 0, 1))
        if grow <= 0:
            continue
        wind = (0.025 + 0.05 * en) * math.sin(0.9 * t + d * 0.7 + code * 0.13) * (d + 1) / 4
        aa = a + wind
        x1, y1 = x + L * grow * math.cos(aa), y + L * grow * math.sin(aa)
        segs.append((x, y, x1, y1, d))
        if d + 1 < TREE_MAX and grow >= 1:
            stack.append((x1, y1, aa - spread, L * TR_RAT, d + 1, code * 2))
            stack.append((x1, y1, aa + spread, L * TR_RAT, d + 1, code * 2 + 1))
        else:
            tips.append((x1, y1, code, d))
    return segs, tips, depth


def harm_at_idx(t):
    return int(np.searchsorted(h_t, t, side="right")) - 1


LEAF_HOLD = 8.0
_rng = np.random.default_rng(9)
LEAF_TIP = _rng.integers(0, 1 << 20, NM)
LEAF_PH = _rng.random(NM) * 6.28
LEAF_FALL = 3.2 + _rng.random(NM) * 2.0


def draw_tree(L, img, E, t, en):
    segs, tips, depth = tree_geom(t, en)
    for x0, y0, x1, y1, d in segs:
        c = hexc("#6B3A1F") * (1 - d / TREE_MAX) + GOLD * 0.6 * (d / TREE_MAX)
        L.lines([(x0, y0), (x1, y1)], c, 0.85, max(1.0, 9 * TR_RAT ** d))
    tips.sort(key=lambda q: q[2])
    if not tips:
        return depth
    j1 = int(np.searchsorted(mt0, t, side="right"))
    j0 = int(np.searchsorted(mt0, t - LEAF_HOLD - 6.0, side="left"))
    for i in range(j0, j1):
        a_ = t - mt0[i]
        tx, ty, _, _ = tips[int(LEAF_TIP[i] % len(tips))]
        col = pcol(mpc[i])
        fl = math.exp(-a_ / 0.35)
        if a_ < LEAF_HOLD:
            x, y, rot, al = tx, ty, LEAF_PH[i], 1.0
        else:
            u = a_ - LEAF_HOLD
            y = ty + 0.5 * 55 * S * u * u + 20 * S * u
            x = tx + 28 * S * math.sin(2.2 * u + LEAF_PH[i]) + 18 * S * u
            rot = LEAF_PH[i] + 2.5 * u
            al = 1 - fs(LEAF_FALL[i] * 0.6, LEAF_FALL[i], u)
            if y > 600 * S:
                al *= max(0.0, 1 - (y - 600 * S) / (30 * S))
        if al <= 0.02:
            continue
        sz = (7 + 6 * mv[i] / 127) * S * (1 + 0.5 * fl)
        c16 = (int(x * 16), int(y * 16)); ax = (int(sz * 16), int(sz * 0.5 * 16))
        colr = tuple(int(min(1, v * (0.9 + 0.5 * fl) + 0.2 * fl) * 255 * al) for v in col)
        cv2.ellipse(L.c, c16, ax, math.degrees(rot), 0, 360, colr, -1, cv2.LINE_AA, 4)
    return depth


# spirala częstotliwości: kąt = klasa dźwięku (obrót = oktawa), promień ∝ częstotliwość
SP_CX, SP_CY = 1625 * S, 300 * S
SP_PLO, SP_PHI = 52, 92
SP_R0 = 235 * S / 2 ** ((SP_PHI - SP_PLO) / 12)


def sp_pt(p):
    th = -math.pi / 2 + 2 * math.pi * (p - 60) / 12
    r = SP_R0 * 2 ** ((p - SP_PLO) / 12)
    return SP_CX + r * math.cos(th), SP_CY + r * math.sin(th)


SP_CURVE = np.array([sp_pt(p) for p in np.arange(SP_PLO, SP_PHI + 0.01, 0.1)])


def draw_spiral(L, img, E, t):
    L.lines(SP_CURVE, GOLD * 0.8 + 0.2, 0.30, 1.6)
    for k in range(12):
        th = -math.pi / 2 + 2 * math.pi * k / 12
        L.lines([(SP_CX, SP_CY), (SP_CX + 240 * S * math.cos(th), SP_CY + 240 * S * math.sin(th))], WHITE, 0.07, 1)
    j1 = int(np.searchsorted(mt0, t, side="right"))
    j0 = max(0, j1 - 32)
    prev = None
    for i in range(j0, j1):
        a_ = t - mt0[i]
        p = float(np.clip(mp[i], SP_PLO, SP_PHI))
        x, y = sp_pt(p)
        al = math.exp(-a_ / 3.0)
        if prev is not None:
            L.lines([prev, (x, y)], 0.5 * (pcol(mpc[i]) + pcol(mpc[i - 1])), 0.6 * al, 1.8)
        prev = (x, y)
    for i in range(j0, j1):
        a_ = t - mt0[i]
        x, y = sp_pt(float(np.clip(mp[i], SP_PLO, SP_PHI)))
        fl = math.exp(-a_ / 0.3)
        L.circle(x, y, (4 + 5 * mv[i] / 127 + 6 * fl) * S, pcol(mpc[i]) * (0.8 + 0.4 * fl) + 0.2 * fl, 0.95 * math.exp(-a_ / 4))
        if a_ < 0.5:
            L.circle(x, y, (8 + 22 * a_ / 0.5) * S, pcol(mpc[i]), 0.7 * (1 - a_ / 0.5), 1.5)
    return j1 - 1


NOTE_PL = ["C", "Cis", "D", "Dis", "E", "F", "Fis", "G", "Gis", "A", "B", "H"]


def draw_fractals(img, E, L, t, en):
    depth = draw_tree(L, img, E, t, en)
    cur = draw_spiral(L, img, E, t)
    blit(img, SPR["tr_t"], TR_X - SPR["tr_t"][0].shape[1] / 2, 548 * S, 0.75)
    blit(img, SPR["tr_f"], TR_X - SPR["tr_f"][0].shape[1] / 2, 576 * S, 0.72)
    nd = int(min(TREE_MAX, math.floor(depth)))
    key = "lev%d" % nd
    if key not in SPR:
        SPR[key] = text_sprite("poziom %d  →  2%s = %d gałązek" % (nd, "⁰¹²³⁴⁵⁶⁷⁸⁹"[nd], 2 ** nd), FONT_L, 19, (0.95, 0.9, 0.82))
    blit(img, SPR[key], TR_X - SPR[key][0].shape[1] / 2, 620 * S, 0.8)
    blit(img, SPR["sp_t"], SP_CX - SPR["sp_t"][0].shape[1] / 2, 548 * S, 0.75)
    blit(img, SPR["sp_f"], SP_CX - SPR["sp_f"][0].shape[1] / 2, 574 * S, 0.72)
    if cur >= 0 and t - mt0[cur] < 1.5:
        p = int(mp[cur])
        key = "hz%d" % p
        if key not in SPR:
            SPR[key] = text_sprite("%s%d  ·  %s Hz" % (NOTE_PL[p % 12], p // 12 - 1, ("%.1f" % (440 * 2 ** ((p - 69) / 12))).replace(".", ",")),
                                   FONT_L, 19, (0.95, 0.9, 0.82))
        blit(img, SPR[key], SP_CX - SPR[key][0].shape[1] / 2, 620 * S, 0.85 * (1 - fs(1.0, 1.5, t - mt0[cur])))


def frac_sprites():
    SPR["tr_t"] = text_sprite("DRZEWO FRAKTALNE · LIŚCIE = NUTY", FONT_M, 17, GOLD * 0.8 + 0.2, spacing=2)
    SPR["tr_f"] = text_sprite("Lₙ₊₁ = 0,72 · Lₙ      kąt ± 24°", FONT_SERIF_I, 25, (1.0, 0.95, 0.88))
    SPR["sp_t"] = text_sprite("SPIRALA CZĘSTOTLIWOŚCI · OBRÓT = OKTAWA", FONT_M, 17, GOLD * 0.8 + 0.2, spacing=2)
    SPR["sp_f"] = text_sprite("r ∝ f = 440 · 2", FONT_SERIF_I, 27, (1.0, 0.95, 0.88), sup="n/12")
    for nm in NNAME:
        SPR["kd_" + nm] = text_sprite(nm, FONT_M, 15 if len(nm) == 1 else 12, (0.42, 0.33, 0.22))
        SPR["kb_" + nm] = text_sprite(nm, FONT_SB, 20 if len(nm) == 1 else 15, (1, 1, 1))
        SPR["kbs_" + nm] = text_sprite(nm, FONT_SB, 14 if len(nm) == 1 else 11, (1, 1, 1))
        SPR["kbk_" + nm] = text_sprite(nm, FONT_SB, 20 if len(nm) == 1 else 15, (0.15, 0.06, 0.03))


CAPS, FIFTH_HL = build_captions()

# ----------------------------------------------------------------------------- stan klatki
STATIC = WHEEL = NOISE = None
SPR = {}


def init_worker():
    global STATIC, WHEEL, NOISE
    STATIC = build_static()
    WHEEL = build_wheel()
    rng = np.random.default_rng(os.getpid())
    NOISE = ((rng.random((H + 32, W + 32, 1)) - 0.5) * 1.5 / 255).astype(np.float32)
    frac_sprites()
    SPR["title"] = text_sprite("Vivaldi", FONT_SERIF_I, 120, GOLD)
    SPR["sub1"] = text_sprite("CZTERY PORY ROKU · JESIEŃ · ALLEGRO", FONT_L, 26, (1, 1, 1), spacing=6)
    SPR["sub2"] = text_sprite("MATEMATYKA MUZYKI", FONT_L, 22, GOLD * 0.9 + 0.1, spacing=8)
    for k, (t, d, a, b, sup) in enumerate(CAPS):
        SPR[f"c{k}a"] = text_sprite(a, FONT_M, 34)
        SPR[f"c{k}b"] = text_sprite(b, FONT_L, 24, (0.85, 0.85, 0.95), sup=sup)


def energy(t):
    d = t - all_t0; k = d >= 0
    return float(np.tanh(np.sum(all_v[k] / 127.0 * np.exp(-d[k] / 0.6)) / 2.5))


def bloom(E):
    q = cv2.resize(E, (W // 4, H // 4), interpolation=cv2.INTER_AREA)
    b1 = cv2.GaussianBlur(q, (0, 0), 2.0 * S)
    e = cv2.resize(q, (W // 8, H // 8), interpolation=cv2.INTER_AREA)
    b2 = cv2.GaussianBlur(e, (0, 0), 3.0 * S)
    s = cv2.resize(e, (W // 16, H // 16), interpolation=cv2.INTER_AREA)
    b3 = cv2.GaussianBlur(s, (0, 0), 3.0 * S)
    up = lambda x: cv2.resize(x, (W // 4, H // 4), interpolation=cv2.INTER_LINEAR)
    comb = 0.8 * b1 + 0.7 * up(b2) + 0.6 * up(b3)
    return cv2.resize(comb, (W, H), interpolation=cv2.INTER_LINEAR)


def render_frame(fi):
    if STATIC is None:
        init_worker()
    t = fi / FPS
    img = STATIC.copy()
    E = np.zeros((H, W, 3), np.float32)
    en = energy(t)
    L = Layer()

    # --- zorza (wstęgi linii)
    for side in (0, 1):
        for i in range(16):
            xs = np.linspace(0, 0.47, 60) if side == 0 else np.linspace(0.58, 1.0, 60)
            u = (xs - xs[0]) / (xs[-1] - xs[0])
            if side == 0:
                base = 0.34 + 0.20 * (1 - u) ** 1.5 - 0.05 * u
            else:
                base = 0.62 - 0.12 * u
            yv = base + 0.035 * np.sin(6 * xs + 0.6 * t + i * 0.18) + 0.012 * i * (1 if side == 0 else -1) \
                + 0.01 * en * np.sin(14 * xs - 2 * t)
            pts = np.stack([xs * W, yv * H], 1)
            c = PINK * (1 - u[:, None]) + VIOLET * u[:, None] if side == 0 else CYAN * (1 - u[:, None]) + PINK * u[:, None]
            cc = c.mean(0) * 0.5 + (GOLD * 0.5 if i % 5 == 0 else c.mean(0) * 0.5)
            L.lines(pts, cc, (0.06 + 0.06 * en) * (1 - abs(i - 8) / 10), 1.4)

    # --- fale na podłodze (każda „raz” w takcie)
    j = int(np.searchsorted(h_t, t, side="right"))
    for hh in HARM[max(0, j - 3):j]:
        a_ = t - hh[0]
        if 0 <= a_ < 2.6:
            R = 1.0 + 7.5 * (1 - (1 - a_ / 2.6) ** 2)
            th = np.linspace(0, 2 * np.pi, 120)
            zc = 15.0
            pts = np.stack(proj(R * np.cos(th) + float(curve(zc, t)), 0, zc + R * 0.5 * np.sin(th)), 1)
            L.lines(pts, pcol(hh[1]) * 0.7 + 0.3 * GOLD, 0.55 * (1 - a_ / 2.6) ** 1.5, 2.2)
    E += L.c.astype(np.float32) / 255; L.c[:] = 0

    # --- koło kwintowe
    x0, y0, x1, y1 = WHEEL["box"]
    lit_m = np.zeros(12)
    on = (mt0 <= t) & (t < mt1 + 0.6)
    for i in np.nonzero(on)[0]:
        lit_m[fifth(mpc[i])] = max(lit_m[fifth(mpc[i])], 0.55 * math.exp(-(t - mt0[i]) / 0.3) + (0.45 if t < mt1[i] else 0.45 * math.exp(-(t - mt1[i]) / 0.25)))
    hi = max(0, int(np.searchsorted(h_t, t, side="right")) - 1)
    hpcs = [fifth(p) for p in HARM[hi][2]] if t >= h_t[0] - 0.05 else []
    hfade = fs(0, 0.2, t - HARM[hi][0])
    table = np.zeros((26, 3), np.float32)
    mode = key_mode(t)
    for k in range(12):
        b = 0.50 + 0.55 * lit_m[k] + (0.30 * hfade if k in hpcs else 0) + 0.05 * en
        table[k] = FCOL[k] * b
        table[k + 12] = FCOL[k] * (0.20 + 0.30 * (0.30 * hfade if k in hpcs else 0) * 3)
    kin = fs(0, 1.0, t - next((ts for ts, l in SEC[::-1] if t >= ts), 0))
    table[11] = np.minimum(table[11] * 0.9 + GOLD * (0.10 + 0.06 * math.sin(t * 2)), 1.0)   # F-dur (tonika)
    table[24] = hexc("#1C0C0A")
    wcol = table[WHEEL["idx"]] * WHEEL["shade"][..., None]
    a = WHEEL["aa"][..., None] * 0.92
    roi = img[y0:y1, x0:x1]
    roi[:] = roi * (1 - a) + wcol * a
    emw = np.where((WHEEL["idx"] < 12)[..., None], np.maximum(wcol - 0.30 * np.stack([FCOL[k] for k in range(12)] + [np.zeros(3)] * 14)[WHEEL["idx"]], 0), 0)
    E[y0:y1, x0:x1] += emw * 0.9 * WHEEL["aa"][..., None] + WHEEL["lines"] * 0.55
    # wnętrze: cięciwy melodii + wielokąt akordu
    j1 = int(np.searchsorted(mt0, t, side="right"))
    for i in range(max(1, j1 - 30), j1):
        if mpc[i] == mpc[i - 1]:
            continue
        a_ = t - mt0[i]
        al = 0.75 * math.exp(-a_ / 2.4) * fs(0, 0.05, a_)
        hl = i in FIFTH_HL and a_ < 3.5
        if al < 0.03 and not hl:
            continue
        p0, p1 = wheel_pt(mpc[i - 1], R_I - 6 * S), wheel_pt(mpc[i], R_I - 6 * S)
        c = 0.5 * (pcol(mpc[i - 1]) + pcol(mpc[i]))
        L.lines([p0, p1], GOLD if hl else c * 0.8 + 0.2, 1.0 if hl else al, 4 if hl else 1.8)
    if hpcs:
        ptsh = [wheel_pt(p, R_I - 14 * S) for p in HARM[hi][2]]
        sc = 0.8 + 0.2 * hfade
        cxy = np.mean(ptsh, 0)
        ptsh = [cxy + (np.array(p) - cxy) * sc for p in ptsh]
        c = pcol(HARM[hi][1])
        L.poly(ptsh, c, 0.25 * hfade)
        L.lines(ptsh, c * 0.6 + 0.4, 0.9 * hfade, 2.5, closed=True)
    E += L.c.astype(np.float32) / 255; L.c[:] = 0
    lab = WHEEL["lab"][..., None]
    roi = img[y0:y1, x0:x1]
    roi[:] = roi * (1 - lab * 0.95) + lab * 0.97
    clef = WHEEL["clef"][..., None]
    roi[:] = roi * (1 - clef * 0.5) + clef * 0.5 * (0.6 * CYAN + 0.4)
    E[y0:y1, x0:x1] += clef * (0.10 + 0.25 * en) * CYAN
    for p in (HARM[hi][2] if hpcs else []):
        x, y = wheel_pt(p, R_I - 14 * S)
        draw_ball(img, E, x, y, (7 + 3 * (p == HARM[hi][1])) * S, pcol(p), alpha=hfade, glow=0.6)

    draw_fractals(img, E, L, t, en)
    E += L.c.astype(np.float32) / 255; L.c[:] = 0

    # --- neonowy tor
    zs = np.concatenate([np.linspace(Z_HIT, 8, 40), np.linspace(8.2, Z_FAR + 2, 40)])
    cz = curve(zs, t)
    half = (len(_whites) * KW) / 2 + 0.12
    lx, ly = proj(-half + cz, 0, zs); rx, ry = proj(half + cz, 0, zs)
    road = np.concatenate([np.stack([lx, ly], 1), np.stack([rx, ry], 1)[::-1]])
    # gradient toru (fiolet blisko → granat daleko) z połyskiem
    m = np.zeros((H, W), np.uint8)
    cv2.fillPoly(m, [np.round(road * 16).astype(np.int32).reshape(-1, 1, 2)], 255, cv2.LINE_AA, 4)
    ys0 = int(max(0, ly.min() - 2))
    mm = m[ys0:].astype(np.float32)[..., None] / 255
    yy = np.linspace(0, 1, H - ys0, dtype=np.float32)[:, None, None] ** 1.3
    rc = hexc("#1E0C08") * (1 - yy) + hexc("#4E1E10") * yy
    img[ys0:] = img[ys0:] * (1 - mm * 0.93) + rc * mm * 0.93
    # pasy (linie co oktawę, na dźwiękach C) i krawędzie neonowe
    for p in range(LOWK, HIGHK + 1):
        if p % 12 == 0:
            xx = key_x(p) - KW / 2
            px, py = proj(xx + cz, 0, zs)
            L.lines(np.stack([px, py], 1), VIOLET * 0.8 + 0.2, 0.22, 1.2)
    sheen = 0.5 + 0.5 * np.sin(zs * 0.8 - t * 2.0)
    for sgn, c0, c1 in ((-1, PINK, VIOLET), (1, GOLD, PINK)):
        px, py = proj(sgn * half + cz, 0, zs)
        pts = np.stack([px, py], 1)
        for k in range(len(zs) - 1):
            u = k / (len(zs) - 1)
            c = c0 * (1 - u) + c1 * u
            L.lines(pts[k:k + 2], c, 0.95 * (1 - 0.6 * u), 5.0 * (1 - 0.6 * u))
    E += L.c.astype(np.float32) / 255; L.c[:] = 0

    # --- ślady nut na torze (długość = czas trwania)
    def note_z(tt):
        return Z_HIT + VZ * (np.asarray(tt) - t)

    vis_m = np.nonzero((mt0 < t + 4.2) & (mt1 > t - 0.05))[0]
    vis_a = np.nonzero((at0 < t + 4.2) & (at1 > t - 0.05))[0]
    for arr, vis, wfac, al in ((ap, vis_a, 0.32, 0.30), (mp, vis_m, 0.40, 0.55)):
        for i in vis:
            t0_, t1_ = (at0[i], at1[i]) if arr is ap else (mt0[i], mt1[i])
            za, zb = max(Z_HIT, float(note_z(t0_))), min(Z_FAR, float(note_z(t1_)))
            if zb <= za:
                continue
            zz = np.linspace(za, zb, 8)
            x = key_x(arr[i]); c_ = curve(zz, t)
            lxx, lyy = proj(x - KW * wfac + c_, 0.002, zz); rxx, ryy = proj(x + KW * wfac + c_, 0.002, zz)
            poly = np.concatenate([np.stack([lxx, lyy], 1), np.stack([rxx, ryy], 1)[::-1]])
            fogf = 1 - fs(Z_FAR - 4, Z_FAR, zb)
            L.poly(poly, pcol(arr[i] % 12), al * fogf)
    E += L.c.astype(np.float32) / 255; L.c[:] = 0
    # kule (od najdalszych)
    balls = []
    for i in vis_m:
        if mt0[i] >= t - 0.12:
            balls.append((float(note_z(mt0[i])), key_x(mp[i]), 0.105 + 0.045 * mv[i] / 127, pcol(mpc[i]), mt0[i]))
    for i in vis_a:
        if at0[i] >= t - 0.12:
            r = 0.085 if ap[i] < 48 else 0.058
            balls.append((float(note_z(at0[i])), key_x(ap[i]), r, pcol(ap[i] % 12) * 0.9 + 0.05, at0[i]))
    balls.sort(key=lambda b: -b[0])
    for z, x, r, c, t0_ in balls:
        if z > Z_FAR:
            continue
        sink = max(0.0, t - t0_)
        zc = max(z, Z_HIT)
        rr = r * (1 - sink / 0.12) if sink > 0 else r
        if rr <= 0.005:
            continue
        cx, cy = proj(x + float(curve(zc, t)), rr - 0.25 * sink, zc)
        fog = 1 - fs(Z_FAR - 3.5, Z_FAR, z)
        draw_ball(img, E, float(cx), float(cy), F * rr / zc, c, alpha=fog, glow=0.6)

    # --- linia uderzenia i klawisze
    hx0, hy0 = proj(-half + float(curve(Z_HIT, t)), 0, Z_HIT); hx1, hy1 = proj(half + float(curve(Z_HIT, t)), 0, Z_HIT)
    L.lines([(hx0, hy0), (hx1, hy1)], GOLD * 0.7 + 0.3, 0.8, 3)
    lit = {}
    for arr, t0a, t1a in ((mp, mt0, mt1), (ap, at0, at1)):
        sel = np.nonzero((t0a <= t) & (t < t1a + 0.25))[0]
        for i in sel:
            v = 0.55 * math.exp(-(t - t0a[i]) / 0.25) + (0.6 if t < t1a[i] else 0.6 * math.exp(-(t - t1a[i]) / 0.08))
            p = int(arr[i])
            if v > lit.get(p, 0):
                lit[p] = min(1.0, v); lit_col[p] = pcol(p % 12)
            a_ = t - t0a[i]
            if a_ < 0.5 and arr is mp:
                x = key_x(p) + float(curve(Z_HIT, t))
                th = np.linspace(0, 2 * np.pi, 48)
                R = 0.08 + 0.35 * (a_ / 0.5) ** 0.6
                pts = np.stack(proj(x + R * np.cos(th), 0.01, Z_HIT + 0.45 * R * np.sin(th)), 1)
                L.lines(pts, pcol(p % 12) * 0.7 + 0.3, 0.9 * (1 - a_ / 0.5), 2.5)
    draw_keyboard(img, lit)
    for p, v in lit.items():
        q = key_quad(p, v)
        L.poly(q, lit_col[p], 0.45 * v)
    E += L.c.astype(np.float32) / 255; L.c[:] = 0
    # podpowiedzi nut na klawiszach
    for p in range(LOWK, HIGHK + 1):
        v = lit.get(p, 0.0)
        q = key_quad(p, v)
        nm = NNAME[p % 12]
        cx = (q[0][0] + q[1][0]) / 2
        if v > 0.05:
            dark = float(lit_col[p] @ np.array([0.3, 0.59, 0.11], np.float32)) > 0.55 and not is_black(p)
            spr = (SPR["kbk_" + nm] if dark else SPR["kb_" + nm]) if not is_black(p) else SPR["kbs_" + nm]
            blit(img, spr, cx - spr[0].shape[1] / 2, q[2][1] - spr[0].shape[0] - (14 if not is_black(p) else 12) * S, min(1, v * 1.5))
        elif not is_black(p):
            spr = SPR["kd_" + nm]
            blit(img, spr, cx - spr[0].shape[1] / 2, q[2][1] - spr[0].shape[0] - 14 * S, 0.55 if p % 12 == 0 else 0.30)
    E += L.c.astype(np.float32) / 255; L.c[:] = 0

    # --- rytm: trzy punkty (raz-dwa-trzy), bez tekstu
    jj = int(np.searchsorted(ae_t, t, side="right")) - 1
    for b in range(4):
        x, y = (1714 + 46 * b) * S, 38 * S
        lv = 0.0
        if jj >= 0:
            for q in range(max(0, jj - 3), jj + 1):
                if AEV[q][1] == b:
                    lv = max(lv, math.exp(-(t - ae_t[q]) / 0.25))
        c = (GOLD, PINK, CYAN, VIOLET)[b]
        draw_ball(img, E, x, y, (9 + 5 * lv) * S, c * (0.45 + 0.55 * lv), glow=0.4 + lv)

    # --- kompozycja + poświata
    out = img + E + 0.8 * bloom(E)
    gfade = fs(0, 0.8, t) * (1 - 0.8 * fs(DUR - 2.0, DUR, t))
    out = out * (0.2 + 0.8 * gfade)
    out = 1 - np.exp(-1.35 * np.maximum(out, 0))
    out = out / (1 - math.exp(-1.35))
    lum = out.mean(2, keepdims=True)
    out = np.clip(lum + (out - lum) * 1.22, 0, 1)

    # --- tekst (subtelny, tylko gdy ma znaczenie)
    ta = fs(0.6, 1.4, t) * (1 - fs(4.4, 5.4, t)) + fs(DUR - 5.0, DUR - 4.0, t) * (1 - fs(DUR - 1.2, DUR - 0.2, t))
    if ta > 0:
        for key, yy_ in (("title", 640), ("sub1", 775), ("sub2", 815)):
            blit(out, SPR[key], W / 2 - SPR[key][0].shape[1] / 2, yy_ * S, ta)
    for k, (t0c, d, a, b, sup) in enumerate(CAPS):
        if t0c - 0.1 <= t <= t0c + d + 0.1:
            al = fs(t0c, t0c + 0.5, t) * (1 - fs(t0c + d - 0.6, t0c + d, t))
            px, py_, pw, ph = 40 * S, 690 * S, max(SPR[f"c{k}a"][0].shape[1], SPR[f"c{k}b"][0].shape[1]) + 50 * S, 112 * S
            roi = out[int(py_):int(py_ + ph), int(px):int(px + pw)]
            roi[:] = roi * (1 - 0.30 * al) + hexc("#3A1A10") * 0.30 * al
            m = np.zeros(roi.shape[:2], np.uint8)
            cv2.rectangle(m, (0, 0), (m.shape[1] - 1, m.shape[0] - 1), 255, max(1, int(1.5 * S)))
            roi += (m.astype(np.float32) / 255 * 0.35 * al)[..., None] * (0.5 * GOLD + 0.5)
            cv2.line(roi, (int(20 * S), int(14 * S)), (int(20 * S), int(ph - 14 * S)), tuple(float(v) * al for v in GOLD), max(1, int(3 * S)))
            blit(out, SPR[f"c{k}a"], px + 30 * S, py_ + 8 * S, al)
            blit(out, SPR[f"c{k}b"], px + 30 * S, py_ + 58 * S, al * 0.9)

    ox, oy = np.random.randint(0, 32, 2)
    out = out + NOISE[oy:oy + H, ox:ox + W]
    o8 = np.clip(out * 255 + 0.5, 0, 255).astype(np.uint8)
    z = 1.0 + 0.05 * (1 - fs(0, 3.0, t)) + 0.01 * (1 + math.sin(2 * math.pi * t / 19)) / 2 + 0.03 * fs(DUR - 5, DUR, t)
    M = np.float32([[z, 0, W / 2 * (1 - z)], [0, z, H * 0.45 * (1 - z)]])
    return cv2.warpAffine(o8, M, (W, H), flags=cv2.INTER_LINEAR, borderMode=cv2.BORDER_REFLECT)


def run_seg(f0, f1, path, procs=None, crf=21):
    procs = procs or int(os.environ.get("PROCS", max(1, (os.cpu_count() or 2) - 1)))
    cmd = ["ffmpeg", "-y", "-loglevel", "error", "-f", "rawvideo", "-pix_fmt", "rgb24", "-s", f"{W}x{H}",
           "-r", str(FPS), "-i", "-", "-vf", "scale=out_color_matrix=bt709:out_range=tv,format=yuv420p",
           "-c:v", "libx264", "-preset", "veryfast", "-crf", str(crf), "-profile:v", "high",
           "-level", "5.1" if S > 1 else "4.1", "-g", "60", "-colorspace", "bt709", "-color_primaries", "bt709",
           "-color_trc", "bt709", "-color_range", "tv", path]
    p = subprocess.Popen(cmd, stdin=subprocess.PIPE)
    with Pool(procs, initializer=init_worker) as pool:
        for k, im in enumerate(pool.imap(render_frame, range(f0, f1), chunksize=2)):
            p.stdin.write(im.tobytes())
            if k % 150 == 0:
                print("klatka", f0 + k, flush=True)
    p.stdin.close()
    p.wait()


if __name__ == "__main__":
    ap_ = argparse.ArgumentParser()
    ap_.add_argument("--test", nargs="*", type=float)
    ap_.add_argument("--seg", nargs=3)
    a = ap_.parse_args()
    if a.test:
        import time
        os.makedirs(os.environ.get("TEST_DIR", os.path.join(HERE, "test")), exist_ok=True)
        init_worker()
        for tt in a.test:
            t0 = time.time()
            im = render_frame(int(round(tt * FPS)))
            fn = os.path.join(HERE, "test", f"neon_{tt:06.2f}.png")
            cv2.imwrite(fn, im[..., ::-1])
            print(fn, f"{time.time() - t0:.2f}s")
    if a.seg:
        run_seg(int(a.seg[0]), int(a.seg[1]), a.seg[2])
