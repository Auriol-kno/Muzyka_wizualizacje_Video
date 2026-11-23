"""Pojedyncze klatki wizualizacji w wybranych chwilach utworu → PNG (podgląd, praca w ComfyUI).

    python skrypty/klatki.py --wav nagranie.wav --preset 3_gory_ze_strun --czasy 62,211 --wyj katalog
    python skrypty/klatki.py --lista          # dostępne presety (JSON)

Te same funkcje i ścieżki kamery co `animacja.py`, więc klatka z chwili t jest identyczna z klatką
klipu w tej chwili (przy tym samym seedzie i podpisie). Render 1920×1080, potem skalowanie lanczos.
"""
import argparse
import json
import multiprocessing as mp
import os
import sys
from pathlib import Path

import numpy as np

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))
sys.path.insert(0, str(ROOT / "skrypty"))

import animacja  # noqa: E402


def presety():
    from wizualizacje.czasteczki import PRESETY
    from wizualizacje.koncepcje_v2 import KONCEPCJE_V2
    return dict(koncepcje_v2=list(KONCEPCJE_V2), czasteczki=list(PRESETY))


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--lista", action="store_true", help="wypisz presety jako JSON i zakończ")
    ap.add_argument("--wav")
    ap.add_argument("--preset", default="3_gory_ze_strun")
    ap.add_argument("--czasy", default="62,211", help="chwile w sekundach, po przecinku")
    ap.add_argument("--rozmiar", default="1280x720")
    ap.add_argument("--podpis", default="")
    ap.add_argument("--seed", type=int, default=20261122)
    ap.add_argument("--procesy", type=int, default=max(1, (os.cpu_count() or 2) // 2))
    ap.add_argument("--wyj", required=False, help="katalog na PNG")
    a = ap.parse_args()
    if a.lista:
        print(json.dumps(presety(), ensure_ascii=False))
        return
    if not a.wav or not a.wyj:
        sys.exit("potrzebne --wav i --wyj")
    p = presety()
    if a.preset not in p["koncepcje_v2"] + p["czasteczki"]:
        sys.exit(f"nieznany preset {a.preset}")
    # sama nazwa pliku → folder [udzial] zrodla; sprawdzamy przed pulą procesów (błąd w inicjalizacji
    # procesu potomnego zawiesiłby pulę zamiast zakończyć skrypt)
    wav = Path(a.wav)
    if not wav.is_absolute() and not wav.exists():
        wav = animacja.sciezki()[0].parent / "zrodla" / wav
        import tomllib
        cfg = ROOT / "config" / "sciezki.toml"
        if cfg.exists():
            with open(cfg, "rb") as f:
                z = tomllib.load(f).get("udzial", {}).get("zrodla")
            if z:
                wav = Path(os.path.expandvars(z)) / Path(a.wav)
    if not wav.exists():
        sys.exit(f"brak pliku dźwięku: {wav}")
    a.wav = str(wav)
    czasy = [float(x) for x in a.czasy.replace(";", ",").split(",") if x.strip()]
    from PIL import Image
    from wizualizacje.czasteczki import W, H
    sz, wy = (int(v) for v in a.rozmiar.lower().split("x"))
    wyj = Path(a.wyj); wyj.mkdir(parents=True, exist_ok=True)
    ctx = mp.get_context("spawn")
    # od = 0, fps = 1 → indeks klatki to po prostu czas w sekundach
    with ctx.Pool(min(a.procesy, len(czasy)), initializer=animacja._init,
                  initargs=(a.wav, a.preset, a.seed, a.podpis, 0.0, 1)) as pool:
        for k, (t, dane) in enumerate(pool.imap(animacja._klatka, czasy)):
            img = Image.fromarray(np.frombuffer(dane, np.uint8).reshape(H, W, 3))
            if (sz, wy) != (W, H):
                img = img.resize((sz, wy), Image.LANCZOS)
            plik = wyj / f"klatka_{k:03d}_{t:08.3f}s.png"
            img.save(plik)
            print(f"{plik}", flush=True)


if __name__ == "__main__":
    main()
