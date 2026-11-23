"""Transkrypcja nagrania (numpy/scipy): melodia (salience harmoniczna + Viterbi), onsety, beat tracking,
akordy z chromy (szablony + wygładzanie), aranżacja fortepianowa → MIDI.
  python transcribe.py wejscie.wav wyjscie.mid
"""
import sys
import json
import numpy as np
from scipy.io import wavfile
from scipy.signal import stft, medfilt, find_peaks
from scipy.ndimage import uniform_filter1d
import sys as _sys
from pathlib import Path as _Path
ROOT = _Path(__file__).resolve().parents[2]
_sys.path.insert(0, str(ROOT / "wspolne"))
from midi_io import write_midi

SR, NFFT, HOP = 22050, 4096, 256
FPS = SR / HOP
P_LO, P_HI, RES = 55, 98, 5           # zakres melodii (MIDI), 1/5 półtonu
LEAD = 1.2                           # sekundy ciszy na początku (intro wideo)


def hz(m):
    return 440.0 * 2 ** ((np.asarray(m, float) - 69) / 12)


def spectrogram(x):
    win = np.hanning(NFFT).astype(np.float32)
    n = 1 + (len(x) - NFFT) // HOP
    out = np.empty((NFFT // 2 + 1, n), np.float32)
    for s in range(0, n, 2000):
        e = min(n, s + 2000)
        idx = (np.arange(s, e) * HOP)[:, None] + np.arange(NFFT)[None, :]
        out[:, s:e] = np.abs(np.fft.rfft(x[idx] * win, axis=1)).T.astype(np.float32)
    return out


def harm_matrix(cands, nbins, nh=10, decay=0.82):
    M = np.zeros((len(cands), nbins), np.float32)
    df = SR / NFFT
    for i, m in enumerate(cands):
        f0 = hz(m)
        for h in range(1, nh + 1):
            b = f0 * h / df
            if b >= nbins - 2:
                break
            w = decay ** (h - 1)
            b0 = int(np.floor(b)); fr = b - b0
            M[i, b0] += w * (1 - fr); M[i, b0 + 1] += w * fr
    return M


def viterbi(S, jump=0.12, cap=2.5):
    n_c, n_t = S.shape
    d = np.abs(np.arange(n_c)[:, None] - np.arange(n_c)[None, :]) / RES
    T = -jump * np.minimum(d, 12) - cap * (d > 0.5) * 0.15
    D = S[:, 0].copy()
    back = np.zeros((n_c, n_t), np.int16)
    for t in range(1, n_t):
        cand = D[None, :] + T
        back[:, t] = np.argmax(cand, axis=1)
        D = cand[np.arange(n_c), back[:, t]] + S[:, t]
    path = np.zeros(n_t, np.int64)
    path[-1] = np.argmax(D)
    for t in range(n_t - 1, 0, -1):
        path[t - 1] = back[path[t], t]
    return path


def beat_track(env, bpm_lo=70, bpm_hi=160, prior=104):
    e = env - env.mean()
    ac = np.correlate(e, e, "full")[len(e) - 1:]
    lags = np.arange(len(ac))
    bpm = 60 * FPS / np.maximum(lags, 1)
    ok = (bpm > bpm_lo) & (bpm < bpm_hi)
    w = np.exp(-0.5 * (np.log2(bpm / prior) / 0.9) ** 2)
    L = int(lags[ok][np.argmax((ac * w)[ok])])
    # programowanie dynamiczne (Ellis 2007)
    n = len(env); score = env.copy(); prev = -np.ones(n, int)
    for i in range(n):
        lo, hi = i - 2 * L, i - L // 2
        if hi <= 0:
            continue
        js = np.arange(max(0, lo), hi)
        pen = -100 * (np.log((i - js) / L)) ** 2 / 10
        k = np.argmax(score[js] + pen)
        score[i] = env[i] + score[js[k]] + pen[k]; prev[i] = js[k]
    i = int(np.argmax(score[-2 * L:])) + n - 2 * L
    beats = []
    while i >= 0:
        beats.append(i); i = prev[i]
    return np.array(beats[::-1]) / FPS, 60 * FPS / L


TRI = []
for r in range(12):
    for q, iv in (("", (0, 4, 7)), ("m", (0, 3, 7)), ("7", (0, 4, 7, 10))):
        v = np.zeros(12); v[[(r + i) % 12 for i in iv]] = 1
        v[r] += 0.5
        TRI.append((r, q, v / np.linalg.norm(v)))


def main(inp, outmid):
    sr, x = wavfile.read(inp)
    x = x.astype(np.float32) / 32768
    if x.ndim > 1:
        x = x.mean(1)
    Sm = spectrogram(x)
    nb, nt = Sm.shape
    logm = np.log1p(200 * Sm / Sm.max()).astype(np.float32)
    # --- onsety (strumień widmowy)
    flux = np.maximum(np.diff(logm, axis=1, prepend=logm[:, :1]), 0).sum(0)
    flux = flux - uniform_filter1d(flux, 40)
    flux = np.maximum(flux, 0); flux /= flux.max()
    lowflux = np.maximum(np.diff(logm[3:60], axis=1, prepend=logm[3:60, :1]), 0).sum(0)
    lowflux = np.maximum(lowflux - uniform_filter1d(lowflux, 40), 0); lowflux /= lowflux.max()
    onsets, _ = find_peaks(flux, height=0.06, distance=int(0.06 * FPS))
    # --- melodia
    cands = np.arange(P_LO, P_HI + 1e-9, 1 / RES)
    M = harm_matrix(cands, nb)
    Sal = M @ logm
    # kara za podharmoniczne: kandydat o oktawę niżej nie może wygrać tylko dzięki parzystym harmonicznym
    Sal = Sal / (np.percentile(Sal, 99) + 1e-6)
    path = viterbi(Sal)
    pitch = cands[path]
    sal = Sal[path, np.arange(nt)]
    rms = np.sqrt(uniform_filter1d(x[:nt * HOP].reshape(nt, HOP).astype(np.float64) ** 2, 1, axis=0).mean(1))
    rmsn = rms / np.percentile(rms, 98)
    voiced = (sal > 0.22) & (rmsn > 0.04)
    voiced = medfilt(voiced.astype(float), 7) > 0.5
    pr = np.round(medfilt(pitch, 5)).astype(int)
    # segmentacja nut
    onset_set = np.zeros(nt, bool); onset_set[onsets] = True
    notes = []
    i = 0
    while i < nt:
        if not voiced[i]:
            i += 1; continue
        j = i + 1
        while j < nt and voiced[j] and pr[j] == pr[i] and not (onset_set[j] and j - i >= 4):
            j += 1
        if (j - i) / FPS >= 0.055:
            v = float(np.clip(40 + 70 * np.sqrt(np.mean(rmsn[i:j])), 40, 108))
            notes.append([i / FPS, j / FPS, int(pr[i]), v])
        i = j
    # scalanie krótkich przerw tej samej wysokości bez onsetu
    mel = []
    for nt_ in notes:
        if mel and mel[-1][2] == nt_[2] and nt_[0] - mel[-1][1] < 0.03 and not onset_set[int(nt_[0] * FPS)]:
            mel[-1][1] = nt_[1]
        else:
            mel.append(nt_)
    # --- beat tracking
    env = uniform_filter1d(0.6 * flux + 0.4 * lowflux, 3)
    beats, bpm = beat_track(env)
    period = np.median(np.diff(beats))
    # --- chroma na uderzenie i akordy
    freqs = np.arange(nb) * SR / NFFT
    okb = (freqs > 60) & (freqs < 2000)
    pcs = np.round(12 * np.log2(freqs[okb] / 440) + 69).astype(int) % 12
    C = np.zeros((12, nt), np.float32)
    for p in range(12):
        C[p] = logm[okb][pcs == p].sum(0)
    chords = []
    for b in range(len(beats) - 1):
        a, e = int(beats[b] * FPS), int(beats[b + 1] * FPS)
        c = C[:, a:max(a + 1, e)].mean(1)
        c = c / (np.linalg.norm(c) + 1e-9)
        sc = np.array([v @ c for _, _, v in TRI])
        chords.append(sc)
    chords = np.array(chords)
    # wygładzanie: Viterbi z premią za pozostanie
    K = len(TRI); D = chords[0].copy(); bk = np.zeros((len(chords), K), int)
    stay = 0.08
    for t in range(1, len(chords)):
        cand = D[None, :] + stay * np.eye(K)
        bk[t] = np.argmax(cand, 1); D = cand[np.arange(K), bk[t]] + chords[t]
    cp = np.zeros(len(chords), int); cp[-1] = np.argmax(D)
    for t in range(len(chords) - 1, 0, -1):
        cp[t - 1] = bk[t, cp[t]]
    # metrum 4/4: faza taktu = maksimum zmian akordów i basu na „raz”
    chg = np.r_[1, (cp[1:] != cp[:-1]).astype(float)]
    lb = np.array([lowflux[int(b * FPS)] for b in beats[:-1]])
    phase = int(np.argmax([chg[ph::4].mean() + lb[ph::4].mean() for ph in range(4)]))
    # --- MIDI: ticki z rzeczywistych uderzeń (mapa tempa), kwantyzacja do 1/4 miary
    PPQ = 480
    bt = beats + LEAD
    pre = int(np.ceil((bt[0]) / period)) + ((4 - phase) % 4)
    # uderzenia przed pierwszym wykrytym, tak aby takt zaczynał się od „raz”
    nb_pre = pre
    pre_t = bt[0] - period * np.arange(nb_pre, 0, -1)
    BT = np.r_[pre_t, bt]
    # przesuń tak, by indeks 0 był wielokrotnością 4 względem fazy
    first_down = nb_pre + phase
    off = (4 - first_down % 4) % 4
    BT = np.r_[BT[0] - period * np.arange(off, 0, -1), BT]
    t0 = BT[0]
    BT = BT - t0 + 0.0  # czas 0 = pierwsze uderzenie (przed nim brak)
    shift = LEAD - t0 + 0.0

    def to_tick(sec):
        s = sec + shift
        return float(np.interp(s, BT, np.arange(len(BT)) * PPQ, left=0, right=None)) if s <= BT[-1] else \
            (len(BT) - 1) * PPQ + (s - BT[-1]) / period * PPQ

    q = PPQ // 4
    mel_ev = []
    for s0, s1, p, v in mel:
        k0 = int(round(to_tick(s0) / q) * q); k1 = int(round(to_tick(s1) / q) * q)
        if k1 <= k0:
            k1 = k0 + q
        mel_ev.append([k0, k1, p, int(v)])
    mel_ev.sort()
    clean = []
    for e in mel_ev:
        if clean and clean[-1][0] == e[0]:
            if e[3] > clean[-1][3]:
                clean[-1] = e
            continue
        if clean and clean[-1][1] > e[0]:
            clean[-1][1] = e[0]
        clean.append(e)
    clean = [e for e in clean if e[1] > e[0]]
    # korekta błędów oktawowych: pojedyncza nuta o oktawę niżej niż sąsiedzi
    for i in range(1, len(clean) - 1):
        p = clean[i][2]
        if p < 64 and clean[i - 1][2] - p >= 8 and clean[i + 1][2] - p >= 8:
            clean[i][2] = p + 12
    # akompaniament (łagodny): bas na 1 i 3, cichy akord na 2 i 4, w średnim rejestrze
    acc = []
    beat_off = len(BT) - len(bt)
    for b in range(len(chords)):
        r, qd, _ = TRI[cp[b]]
        k = (b + beat_off) * PPQ
        rms_b = float(np.mean(rmsn[int(beats[b] * FPS):int(beats[b + 1] * FPS) + 1]))
        vel = int(np.clip(30 + 34 * np.sqrt(rms_b), 28, 66))
        pos = (b + beat_off) % 4
        if pos in (0, 2):
            bass = 43 + ((r - 43) % 12)
            acc.append((k, k + 2 * PPQ - 40, bass, vel + 4))
        else:
            ivs = {"": (0, 4, 7), "m": (0, 3, 7), "7": (0, 4, 10)}[qd]
            for j, iv in enumerate(sorted(55 + ((r + iv - 55) % 12) for iv in ivs)):
                acc.append((k + j * 24, k + PPQ - 30, j and iv or iv, vel - 10))
    tempo = []
    for i in range(len(BT) - 1):
        tempo.append((i * PPQ, int((BT[i + 1] - BT[i]) * 1e6)))
    write_midi(outmid, [("Melodia", 0, [tuple(e) for e in clean]), ("Akompaniament", 1, acc)], PPQ, tempo, (4, 4),
               [(0, "start")], "Vivaldi - Jesien - Allegro (transkrypcja)")
    info = dict(bpm=float(bpm), n_mel=len(clean), n_beats=len(beats), phase=phase, lead=LEAD, shift=shift,
                chords=[TRI[c][0] * 3 + "m7".find(TRI[c][1]) + 1 for c in cp[:16]])
    json.dump(info, open(outmid + ".json", "w"))
    print(info)


if __name__ == "__main__":
    main(sys.argv[1], sys.argv[2])
