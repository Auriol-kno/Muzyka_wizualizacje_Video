"""Fortepian – synteza modelowa (bez próbek): struny z nieharmonicznością, 1–3 struny na klawisz
(dudnienie), widmo młotka zależne od siły uderzenia, dwuetapowe wybrzmiewanie, tłumiki, pedał,
rezonans płyty rezonansowej i pogłos sali. Wejście: MIDI, wyjście: WAV 48 kHz stereo.
  python piano_synth2.py plik.mid wyjscie.wav DŁUGOŚĆ_S
"""
import os
import sys
import numpy as np
from scipy.io import wavfile
from scipy.signal import butter, lfilter, fftconvolve, sosfilt
import os as _os, sys as _sys
_sys.path.insert(0, _os.path.dirname(_os.path.abspath(__file__)))
from midi_io import read_midi_full

SR = 48000


def note_wave(m, vel, t_off, rng):
    """Zwraca (L, R) dla jednej struny/klawisza; t_off = czas zwolnienia tłumika [s]."""
    f0 = 440.0 * 2 ** ((m - 69) / 12) * 2 ** ((0.012 * (m - 69) ** 2 * np.sign(m - 69) / 100) / 12)
    v = vel / 127.0
    B = 3.0e-4 * 2 ** ((m - 60) / 12 * 0.8)
    tau1 = float(np.clip(2.6 * (261.6 / f0) ** 0.62, 0.22, 7.0))
    damp = 1.0 if m >= 89 else float(np.clip(0.07 + 0.20 * (60 - m) / 30, 0.06, 0.30))
    L = min(t_off + 6 * damp, 7.5 * tau1 * 0.9 + 0.3, 9.0)
    n_s = int(L * SR)
    t = np.arange(n_s, dtype=np.float32) / SR
    nstr = 1 if m < 35 else (2 if m < 48 else 3)
    nmax = int(min(60, 11000 / f0))
    n = np.arange(1, nmax + 1)
    fn = n * f0 * np.sqrt(1 + B * n * n)
    keep = fn < 15000
    n, fn = n[keep], fn[keep]
    # widmo młotka: miejsce uderzenia 1/8, filtr zależny od siły
    hammer = 0.30 + 0.70 * np.abs(np.sin(np.pi * n / 8.3))
    fc = 1100 + 3600 * v ** 1.4
    amp = n ** -0.72 * hammer / (1 + (fn / fc) ** 2.6) * np.exp(-(n - 1) * 0.03) * rng.uniform(0.85, 1.15, len(n))
    if m < 45:
        amp[0] *= 0.45; amp[1:2] *= 0.85
    taun = tau1 / (1 + (fn / 1700.0) ** 1.35 + 0.10 * (n - 1))
    out_l = np.zeros(n_s, np.float32); out_r = np.zeros(n_s, np.float32)
    pan = float(np.clip((m - 64) / 44, -0.8, 0.8))
    for s in range(nstr):
        det = 0.0 if nstr == 1 else rng.normal(0, 0.45) * 1e-2 / 12 * np.log(2) * 0.6
        detf = np.exp(det * 12 * 1.0)
        ph = rng.uniform(0, 2 * np.pi, len(n))
        acc = np.zeros(n_s, np.float32)
        for k in range(0, len(n), 8):
            sl = slice(k, k + 8)
            env = 0.68 * np.exp(-t[None, :] / (taun[sl, None] * 0.22)) + 0.32 * np.exp(-t[None, :] / taun[sl, None])
            acc += (amp[sl, None] * env * np.sin(2 * np.pi * fn[sl, None] * detf * t[None, :] + ph[sl, None])).sum(0)
        g = 1.0 / nstr
        sp = pan + (s - (nstr - 1) / 2) * 0.12
        th = (np.clip(sp, -1, 1) + 1) * np.pi / 4
        out_l += acc * g * np.cos(th); out_r += acc * g * np.sin(th)
    # narastanie i tłumik
    att = np.minimum(1.0, t / (0.0035 + 0.003 * (1 - v)))
    rel = np.where(t > t_off, np.exp(-(t - t_off) / damp), 1.0).astype(np.float32)
    gain = 0.20 * (0.30 + 0.70 * v) ** 1.6 * (1.0 + 0.25 * np.clip((60 - m) / 30, 0, 1)) * (1.0 + 0.15 * np.clip((m - 72) / 20, 0, 1))
    shape = (att * rel * gain).astype(np.float32)
    out_l *= shape; out_r *= shape
    # uderzenie młotka: krótki szum + „puknięcie” płyty
    kn = int(0.04 * SR)
    noise = rng.standard_normal(kn).astype(np.float32)
    lo, hi = min(0.45, 1.5 * f0 / (SR / 2)), min(0.48, 6 * f0 / (SR / 2) + 0.02)
    b, a = butter(2, [max(lo, 0.003), max(hi, lo + 0.01)], btype="band")
    knock = lfilter(b, a, noise) * np.exp(-np.arange(kn) / SR / 0.008) * 0.035 * v ** 2
    thump = np.sin(2 * np.pi * 95 * np.arange(kn) / SR) * np.exp(-np.arange(kn) / SR / 0.018) * 0.015 * v ** 2
    out_l[:kn] += (knock + thump) * 0.9; out_r[:kn] += (knock + thump) * 0.9
    return out_l, out_r


def soundboard_ir(rng):
    n = int(0.25 * SR)
    t = np.arange(n) / SR
    x = rng.standard_normal(n) * np.exp(-t / 0.030)
    sos = butter(2, [90 / (SR / 2), 4500 / (SR / 2)], btype="band", output="sos")
    x = sosfilt(sos, x)
    x /= np.abs(x).max()
    ir = x * 0.35
    ir[0] += 1.0
    return ir.astype(np.float32)


def room_ir(rng, rt60=2.4, length=3.0):
    n = int(length * SR)
    t = np.arange(n) / SR
    irs = []
    for ch in range(2):
        x = rng.standard_normal(n)
        x = lfilter([0.25], [1, -0.75], x)
        x *= np.exp(-6.9 * t / rt60) * np.minimum(1, t / 0.03)
        x[: int(0.025 * SR)] = 0
        for d, g in ((0.011, .7), (0.017, .55), (0.023, .5), (0.031, .45), (0.043, .4), (0.059, .3)):
            x[int((d + 0.002 * ch) * SR)] += g * 0.05
        irs.append((x / np.sqrt((x ** 2).sum())).astype(np.float32))
    return irs


def biquad(kind, f0, gain_db, q):
    A = 10 ** (gain_db / 40); w = 2 * np.pi * f0 / SR; al = np.sin(w) / (2 * q); c = np.cos(w)
    if kind == "peak":
        b = [1 + al * A, -2 * c, 1 - al * A]; a = [1 + al / A, -2 * c, 1 - al / A]
    elif kind == "low":
        sq = 2 * np.sqrt(A) * al
        b = [A * ((A + 1) - (A - 1) * c + sq), 2 * A * ((A - 1) - (A + 1) * c), A * ((A + 1) - (A - 1) * c - sq)]
        a = [(A + 1) + (A - 1) * c + sq, -2 * ((A - 1) + (A + 1) * c), (A + 1) + (A - 1) * c - sq]
    else:
        sq = 2 * np.sqrt(A) * al
        b = [A * ((A + 1) + (A - 1) * c + sq), -2 * A * ((A - 1) + (A + 1) * c), A * ((A + 1) + (A - 1) * c - sq)]
        a = [(A + 1) - (A - 1) * c + sq, 2 * ((A - 1) - (A + 1) * c), (A + 1) - (A - 1) * c - sq]
    return np.array(b) / a[0], np.array(a) / a[0]


def synth(midi, wav, dur):
    rng = np.random.default_rng(2026)
    notes, ppq, _ = read_midi_full(midi)
    # pedał: akompaniament (bas + akordy) brzmi do następnej „raz” w takcie
    bar_ticks = 3 * ppq
    down = {}
    for x in notes:
        down.setdefault(x["k0"] // bar_ticks, x["t0"])
    for x in notes:
        if x["k0"] % bar_ticks == 0:
            down[x["k0"] // bar_ticks] = min(down.get(x["k0"] // bar_ticks, 1e9), x["t0"])
    total = int((dur + 3) * SR)
    Lm = np.zeros(total, np.float32); Rm = np.zeros(total, np.float32)
    for i, x in enumerate(notes):
        toff = x["t1"] - x["t0"]
        if x["ch"] == 1 and os.environ.get("PEDAL", "1") == "1":
            nb = x["k0"] // bar_ticks + 1
            if nb in down:
                toff = max(toff, down[nb] - x["t0"] - 0.03)
            else:
                toff = max(toff, 3.0)
        vel = x["vel"] * (1.06 if x["ch"] == 0 else 0.86) * (1 + rng.normal(0, 0.05))
        l, r = note_wave(x["pitch"], float(np.clip(vel, 20, 120)), toff, rng)
        dt = float(np.clip(rng.normal(0, 0.006), -0.015, 0.015)) if x["t0"] > 0.05 else 0.0
        s = max(0, int(round((x["t0"] + dt) * SR))); e = min(total, s + len(l))
        Lm[s:e] += l[:e - s]; Rm[s:e] += r[:e - s]
        if i % 100 == 0:
            print("nuta", i, "/", len(notes), flush=True)
    sb = soundboard_ir(rng)
    Lm = fftconvolve(Lm, sb)[:total]; Rm = fftconvolve(Rm, sb)[:total]
    irl, irr = room_ir(rng)
    wl = fftconvolve(Lm, irl)[:total]; wr = fftconvolve(Rm, irr)[:total]
    L = Lm + 0.30 * wl + 0.08 * wr
    R = Rm + 0.30 * wr + 0.08 * wl
    n = int(dur * SR)
    L, R = L[:n], R[:n]
    tt = np.arange(n) / SR
    fs_ = dur - 1.6
    fade = np.where(tt > fs_, np.cos(np.clip((tt - fs_) / 1.6, 0, 1) * np.pi / 2) ** 2, 1.0)
    sos = butter(2, 70 / (SR / 2), btype="high", output="sos")
    L = sosfilt(sos, L * fade); R = sosfilt(sos, R * fade)
    for kind, f0, g, q in (("low", 220, -3.0, .7), ("peak", 2800, 2.5, .9), ("high", 7500, 2.5, .7)):
        bb, aa = biquad(kind, f0, g, q)
        L = lfilter(bb, aa, L); R = lfilter(bb, aa, R)
    st = np.stack([L, R], 1)
    st = st / np.abs(st).max() * 0.89
    st = np.tanh(st * 1.1) / np.tanh(1.1)
    wavfile.write(wav, SR, (st * 32767).astype(np.int16))


if __name__ == "__main__":
    synth(sys.argv[1], sys.argv[2], float(sys.argv[3]))
    print("ok")
