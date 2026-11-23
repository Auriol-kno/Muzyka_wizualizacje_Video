"""Podglądy koncepcji wersji 2 (`wizualizacje/koncepcje_v2.py`).

Kadry: cicho (azymut 20°), głośno (20°), głośno z drugiej strony orbity (140°) + opcjonalnie krótki
klip z obrotem kamery i dźwiękiem (--klipy), żeby było widać ruch kamery i światła.

  python skrypty/koncepcje2_podglad.py --wav <nagranie.wav> [--tylko 1_wyspa_poziomic ...] [--klipy] [--sekundy 6]
"""
import argparse
import json
import multiprocessing as mp
import os
import subprocess
import sys
import time
import tomllib
from pathlib import Path

import numpy as np
from PIL import Image

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))
from wizualizacje.analiza import analizuj              # noqa: E402
from wizualizacje.koncepcje_v2 import KONCEPCJE_V2     # noqa: E402
from wizualizacje.czasteczki import W, H               # noqa: E402

FPS = 30


def katalog(arg):
    if arg:
        return Path(arg)
    cfg = ROOT / "config" / "sciezki.toml"
    if cfg.exists():
        with open(cfg, "rb") as f:
            return Path(os.path.expandvars(tomllib.load(f)["udzial"]["robocze"])) / "koncepcje_v2_wariacja2"
    return ROOT / "robocze" / "koncepcje_v2_wariacja2"


def chwile(an):
    i0, i1 = an.idx(8.0), an.idx(an.dlugosc - 8.0)
    e = an.rms_env[i0:i1]
    glosno = float(an.czas[i0 + int(np.argmax(e))])
    cel = np.percentile(e, 30)
    cicho = float(an.czas[i0 + int(np.argmin(np.abs(e - cel) + (an.czas[i0:i1] < 20) * 9))])
    return cicho, glosno


_AN = None
_ZAD = None


def _init(wav, nazwa):
    global _AN, _ZAD
    _AN = analizuj(wav)
    _ZAD = KONCEPCJE_V2[nazwa]


def _klatka(arg):
    t, az = arg
    img, _ = _ZAD(_AN.cechy(t), t, _AN, az)
    return (np.clip(img, 0, 1) * 255).astype(np.uint8).tobytes()


def klip(wav, nazwa, t0, sek, out, az0=10.0, obrot=50.0, procesy=8):
    n = int(sek * FPS)
    zad = [(t0 + i / FPS, az0 + obrot * i / max(n - 1, 1)) for i in range(n)]
    ff = subprocess.Popen(["ffmpeg", "-v", "error", "-y", "-f", "rawvideo", "-pix_fmt", "rgb24", "-s", f"{W}x{H}",
                           "-r", str(FPS), "-i", "-", "-ss", f"{t0:.3f}", "-t", f"{sek:.3f}", "-i", str(wav),
                           "-map", "0:v", "-map", "1:a", "-c:v", "libx264", "-preset", "medium", "-crf", "18",
                           "-pix_fmt", "yuv420p", "-c:a", "aac", "-b:a", "192k", "-ar", "48000", "-shortest",
                           "-movflags", "+faststart", str(out)], stdin=subprocess.PIPE)
    ctx = mp.get_context("spawn")
    with ctx.Pool(procesy, initializer=_init, initargs=(str(wav), nazwa)) as pool:
        for b in pool.imap(_klatka, zad, chunksize=2):
            ff.stdin.write(b)
    ff.stdin.close(); ff.wait()


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--wav", required=True)
    ap.add_argument("--out")
    ap.add_argument("--tylko", nargs="*")
    ap.add_argument("--klipy", action="store_true")
    ap.add_argument("--bez-kadrow", action="store_true")
    ap.add_argument("--sekundy", type=float, default=6.0)
    ap.add_argument("--procesy", type=int, default=max(1, (os.cpu_count() or 2) // 2))
    a = ap.parse_args()
    out = katalog(a.out); out.mkdir(parents=True, exist_ok=True)
    an = analizuj(a.wav)
    cicho, glosno = chwile(an)
    kadry = [("cicho_az20", cicho, 20.0), ("glosno_az20", glosno, 20.0), ("glosno_az140", glosno, 140.0)]
    plik_m = out / "manifest.json"
    manifest = json.loads(plik_m.read_text(encoding="utf-8")) if plik_m.exists() else {}
    manifest.update(wav=str(a.wav), chwile=dict(cicho=round(cicho, 2), glosno=round(glosno, 2)))
    for nazwa, fn in KONCEPCJE_V2.items():
        if a.tylko and nazwa not in a.tylko:
            continue
        if not a.bez_kadrow:
            for etyk, t, az in kadry:
                t0 = time.time()
                img, par = fn(an.cechy(t), t, an, az)
                Image.fromarray((np.clip(img, 0, 1) * 255).astype(np.uint8)).save(out / f"{nazwa}_{etyk}.png")
                jas = float(np.percentile(img.mean(2), 99) * 255)
                print(f"{nazwa} {etyk} t={t:.1f}s  {time.time() - t0:.1f} s  p99={jas:.0f}  {par}", flush=True)
                manifest[f"{nazwa}_{etyk}"] = dict(t=round(t, 2), azymut=az, parametry=par)
        if a.klipy:
            t0 = time.time()
            start = max(0.0, glosno - a.sekundy / 2)
            klip(a.wav, nazwa, start, a.sekundy, out / f"{nazwa}_orbita.mp4", procesy=a.procesy)
            print(f"{nazwa} klip {a.sekundy:.0f} s → {time.time() - t0:.0f} s", flush=True)
    plik_m.write_text(json.dumps(manifest, ensure_ascii=False, indent=1, default=str), encoding="utf-8")


if __name__ == "__main__":
    main()
