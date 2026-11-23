"""Klip „Piasek fraktalny” z dźwięku: MP4 (wideo lub audio) → analiza → klatki PNG (wznawialne) → MP4.

    python skrypty/piasek.py --zrodlo klip_lub_dzwiek.mp4 [--wyj wynik.mp4] [--procesy 6] [--seed 20261123]

Dźwięk wynikowego klipu to NIEZMIENIONA ścieżka źródła (kopia strumienia AAC, bez normalizacji, bez zmiany
tempa i wysokości). Klatki zapisywane w <robocze>/piasek/<nazwa>/klatki – przerwany render wznawia się od
brakujących klatek. Po zakodowaniu: kontrola jakości jak w potoku (`.qc.json`).
"""
import argparse
import json
import multiprocessing as mp
import os
import subprocess
import sys
import time
from pathlib import Path

import numpy as np

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT)); sys.path.insert(0, str(ROOT / "skrypty"))

import animacja  # noqa: E402  (ścieżki, ffmpeg, kontrola)

_S = {}


def _init(wav, n, seed, modul):
    import cv2
    cv2.setNumThreads(1)
    from wizualizacje.analiza import analizuj
    import importlib
    P = importlib.import_module(f"wizualizacje.{modul}")
    an = analizuj(wav)
    _S.update(P=P, p=P.parametry(an, n), sw=P.Swiat(seed))


def _klatka(zadanie):
    import cv2
    k, plik = zadanie
    P = _S["P"]
    img = P.wywolaj(P.klatka(_S["sw"], _S["p"], k), _S["sw"])
    tmp = plik.with_suffix(".tmp.png")
    cv2.imwrite(str(tmp), cv2.cvtColor(img, cv2.COLOR_RGB2BGR))
    os.replace(tmp, plik)                     # klatka zapisana w całości albo wcale
    return k


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--zrodlo", required=True, help="plik z dźwiękiem (MP4/WAV/…)")
    ap.add_argument("--wyj")
    ap.add_argument("--procesy", type=int, default=max(1, (os.cpu_count() or 2) // 2))
    ap.add_argument("--seed", type=int, default=20261123)
    ap.add_argument("--crf", type=int, default=18)
    ap.add_argument("--wersja", choices=["3d", "2d"], default="3d", help="3d: ziarna w przestrzeni (domyślnie)")
    ap.add_argument("--od-klatki", type=int, default=0, help="tylko test: zakres klatek")
    ap.add_argument("--do-klatki", type=int, default=0)
    a = ap.parse_args()
    import importlib
    modul = "piasek3d" if a.wersja == "3d" else "piasek"
    P = importlib.import_module(f"wizualizacje.{modul}")
    zr = Path(a.zrodlo)
    wyniki, robocze = animacja.sciezki()
    nazwa = f"piasek_fraktalny{'_3d' if a.wersja == '3d' else ''}_{zr.stem[:50]}"
    rob = robocze / "piasek" / nazwa; kl = rob / "klatki"; kl.mkdir(parents=True, exist_ok=True)
    wav = rob / "audio.wav"
    if not wav.exists():   # tylko do analizy; do klipu idzie oryginalny strumień
        animacja.ff("-y", "-i", str(zr), "-vn", "-c:a", "pcm_s24le", str(wav))
    pr = subprocess.run(["ffprobe", "-v", "error", "-select_streams", "a:0", "-show_entries",
                         "stream=duration,codec_name", "-of", "json", str(zr)], capture_output=True, text=True)
    a_info = json.loads(pr.stdout)["streams"][0]
    dl = float(a_info["duration"])
    n = int(round(dl * P.FPS))
    zakres = range(a.od_klatki, a.do_klatki or n)
    brak = [(k, kl / f"{k:05d}.png") for k in zakres if not (kl / f"{k:05d}.png").exists()]
    print(f"dźwięk {dl:.3f} s ({a_info['codec_name']}), klatek {n} @ {P.FPS} fps; do zrobienia {len(brak)}", flush=True)
    t0 = time.time()
    if brak:
        with mp.get_context("spawn").Pool(min(a.procesy, len(brak)), initializer=_init,
                                          initargs=(str(wav), n, a.seed, modul)) as pool:
            for j, _ in enumerate(pool.imap_unordered(_klatka, brak), 1):
                if j % 10 == 0 or j == len(brak):
                    el = time.time() - t0
                    print(f"  klatka {j}/{len(brak)}  {el / j:.2f} s/kl.  zostało ~{(len(brak) - j) * el / j / 60:.1f} min",
                          flush=True)
    if a.do_klatki:
        print("test zakresu – bez kodowania"); return
    out = Path(a.wyj) if a.wyj else wyniki / f"{nazwa}_1280x720_25fps.mp4"
    kopia_audio = a_info["codec_name"] == "aac"
    p = animacja.ff("-y", "-framerate", str(P.FPS), "-i", str(kl / "%05d.png"), "-i", str(zr),
                    "-map", "0:v", "-map", "1:a:0", "-c:v", "libx264", "-preset", "slow", "-crf", str(a.crf),
                    "-pix_fmt", "yuv420p", "-r", str(P.FPS), "-fps_mode", "cfr",
                    *(["-c:a", "copy"] if kopia_audio else ["-c:a", "aac", "-b:a", "256k", "-ar", "48000"]),
                    "-movflags", "+faststart", str(out))
    if p.returncode:
        sys.exit(p.stderr[-2000:])
    qc = animacja.kontrola(out, n / P.FPS, P.FPS)
    raport = dict(plik=str(out), zrodlo=str(zr), seed=a.seed, klatki=n, fps=P.FPS, rozmiar=f"{getattr(P, 'W_OUT', P.W)}x{getattr(P, 'H_OUT', P.H)}", wersja=a.wersja,
                  audio="kopia strumienia źródła" if kopia_audio else "AAC 256k", kontrola=qc,
                  czas_renderu_min=round((time.time() - t0) / 60, 1))
    with open(out.with_suffix(".qc.json"), "w", encoding="utf-8") as f:
        json.dump(raport, f, ensure_ascii=False, indent=2)
    print(json.dumps(qc, ensure_ascii=False, indent=2))
    print(("OK" if qc["ok"] else "UWAGA: kontrola nie przeszła") + f" → {out}")


if __name__ == "__main__":
    main()
