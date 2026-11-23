"""Pomiar audio (bez interpretacji artystycznej).

Liczy w ramkach co HOP próbek:
  - RMS (głośność) i obwiednię z szybkim atakiem i wolniejszym zanikiem (jak fortepian),
  - energię pasm: niskie 30–250 Hz, średnie 250–2000 Hz, wysokie 2–8 kHz (też z obwiednią),
  - centroid widmowy (jasność barwy w Hz),
  - siłę ataku (strumień widmowy) i listę ataków,
  - najsilniejsze szczyty widma 80–4000 Hz (UWAGA: w wielogłosowym fortepianie to mieszanina tonów
    podstawowych różnych dźwięków i ich alikwotów – nie traktujemy ich jako harmonicznych jednego tonu),
  - chromę (12 klas wysokości) do oceny „ile różnych dźwięków brzmi naraz”.
Wszystko jest deterministyczne dla danego pliku.
"""
from dataclasses import dataclass, field
import math
import numpy as np
from scipy.io import wavfile
from scipy.signal import find_peaks

SR = 22050
NFFT = 8192
HOP = 512


def wczytaj_wav(sciezka):
    sr, x = wavfile.read(str(sciezka))
    x = x.astype(np.float32)
    if x.ndim > 1:
        x = x.mean(1)
    x = x / (np.abs(x).max() + 1e-9)
    if sr != SR:  # proste przepróbkowanie (wystarczy do analizy)
        n = int(len(x) * SR / sr)
        x = np.interp(np.linspace(0, len(x) - 1, n), np.arange(len(x)), x).astype(np.float32)
    return x


def obwiednia(v, atak=0.03, zanik=0.6, fps=SR / HOP):
    """Szybki atak, spokojny zanik (stałe czasowe w sekundach)."""
    ka = 1 - math.exp(-1 / (atak * fps)); kz = 1 - math.exp(-1 / (zanik * fps))
    out = np.empty_like(v); y = 0.0
    for i, s in enumerate(v):
        y += (ka if s > y else kz) * (s - y)
        out[i] = y
    return out


@dataclass
class Analiza:
    czas: np.ndarray
    rms: np.ndarray
    rms_env: np.ndarray
    pasma_env: np.ndarray          # (3, T): niskie, średnie, wysokie – znormalizowane 0..1
    centroid: np.ndarray           # Hz
    atak: np.ndarray               # siła ataku 0..1
    ataki: np.ndarray              # czasy ataków [s]
    chroma: np.ndarray             # (12, T)
    mag: np.ndarray = field(repr=False, default=None)
    freqs: np.ndarray = field(repr=False, default=None)
    dlugosc: float = 0.0

    def idx(self, t):
        return int(np.clip(round(t * SR / HOP), 0, len(self.czas) - 1))

    def szczyty(self, t, n=6, fmin=80, fmax=4000):
        """Najsilniejsze szczyty widma w chwili t: lista (f [Hz], względna siła 0..1)."""
        i = self.idx(t)
        m = self.mag[:, max(0, i - 2):i + 3].mean(1)
        ok = (self.freqs >= fmin) & (self.freqs <= fmax)
        mm = np.where(ok, m, 0)
        if mm.max() <= 1e-9:
            return []
        pk, pr = find_peaks(mm, prominence=mm.max() * 0.08, distance=6)
        pk = pk[np.argsort(-mm[pk])][:n]
        out = []
        for p in pk:
            a, b, c = mm[p - 1], mm[p], mm[p + 1]   # interpolacja paraboliczna
            d = 0.5 * (a - c) / (a - 2 * b + c + 1e-12)
            out.append(((p + d) * SR / NFFT, float(b / mm.max())))
        return out

    def cechy(self, t, okno=4.0):
        """Zestaw cech w chwili t (pomiar; interpretacja jest w presetach)."""
        i = self.idx(t)
        ch = self.chroma[:, max(0, i - 8):i + 1].mean(1)
        ch = ch / (ch.max() + 1e-9)
        ost = self.ataki[(self.ataki <= t) & (self.ataki > t - okno)]
        impuls = float(np.sum(np.exp(-(t - ost) / 0.15))) if len(ost) else 0.0
        return dict(
            t=float(t),
            energia=float(self.rms_env[i]),
            niskie=float(self.pasma_env[0, i]), srednie=float(self.pasma_env[1, i]), wysokie=float(self.pasma_env[2, i]),
            centroid_hz=float(self.centroid[i]),
            gestosc_atakow=float(len(ost) / okno),           # ataki na sekundę w oknie
            impuls_ataku=float(min(1.0, impuls)),
            wielodzwiek=int((ch > 0.45).sum()) if self.rms_env[i] > 0.03 else 0,
            szczyty=[(round(f, 1), round(a, 3)) for f, a in self.szczyty(t)],
        )


def analizuj(sciezka):
    x = wczytaj_wav(sciezka)
    x = x / (np.abs(x).max() + 1e-9)
    n = 1 + max(0, (len(x) - NFFT)) // HOP
    win = np.hanning(NFFT).astype(np.float32)
    mag = np.empty((NFFT // 2 + 1, n), np.float32)
    for s in range(0, n, 512):
        e = min(n, s + 512)
        idx = (np.arange(s, e) * HOP)[:, None] + np.arange(NFFT)[None, :]
        idx = np.minimum(idx, len(x) - 1)
        mag[:, s:e] = np.abs(np.fft.rfft(x[idx] * win, axis=1)).T
    freqs = np.arange(NFFT // 2 + 1) * SR / NFFT
    czas = (np.arange(n) * HOP + NFFT / 2) / SR
    rms = np.sqrt(np.array([np.mean(x[i * HOP:i * HOP + NFFT] ** 2) for i in range(n)]))
    ref = np.percentile(rms, 98) + 1e-9
    rmsn = np.clip(rms / ref, 0, 1.5)
    p2 = mag ** 2
    pasma = []
    for lo, hi in ((30, 250), (250, 2000), (2000, 8000)):
        b = p2[(freqs >= lo) & (freqs < hi)].sum(0)
        b = np.sqrt(b); b = np.clip(b / (np.percentile(b, 98) + 1e-9), 0, 1.5)
        pasma.append(obwiednia(b))
    centroid = (p2 * freqs[:, None]).sum(0) / (p2.sum(0) + 1e-12)
    lm = np.log1p(100 * mag / (mag.max() + 1e-9))
    flux = np.maximum(np.diff(lm, axis=1, prepend=lm[:, :1]), 0).sum(0)
    base = np.convolve(flux, np.ones(31) / 31, mode="same")
    fl = np.maximum(flux - base, 0)
    fl = fl / (np.percentile(fl, 99.5) + 1e-9)
    pk, _ = find_peaks(fl, height=0.25, distance=int(0.07 * SR / HOP))
    pk = pk[rmsn[pk] > 0.03]
    chroma = np.zeros((12, n), np.float32)
    ok = (freqs > 60) & (freqs < 2500)
    pc = np.round(12 * np.log2(freqs[ok] / 440) + 69).astype(int) % 12
    for k in range(12):
        chroma[k] = mag[ok][pc == k].sum(0)
    return Analiza(czas=czas, rms=rmsn, rms_env=obwiednia(rmsn), pasma_env=np.array(pasma), centroid=centroid,
                   atak=np.clip(fl, 0, 1), ataki=czas[pk], chroma=chroma, mag=mag, freqs=freqs, dlugosc=len(x) / SR)


def pierwsza_fraza(a: Analiza, po_ataku=1.6):
    """Chwila w pierwszej słyszalnej frazie: pierwszy atak powyżej progu głośności + ~1,6 s."""
    if len(a.ataki) == 0:
        return float(min(a.dlugosc / 4, 5.0))
    return float(min(a.ataki[0] + po_ataku, a.dlugosc))
