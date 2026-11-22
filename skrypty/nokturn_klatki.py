"""Chopin – Nokturn Es-dur op. 9 nr 2: 5 kierunków wizualnych × 2 klatki (początek i środek tego samego
wykonania), każda 1920×1080 PNG, plus manifest i arkusz porównawczy.

  python skrypty/nokturn_klatki.py --audio nagranie.wav --zrodlo "wykonawca, źródło, licencja"
  python skrypty/nokturn_klatki.py --demo          # TRYB DEMO: syntetyczny sygnał testowy, NIE Chopin

Tryb demo istnieje tylko do sprawdzenia grafiki i eksportu, dopóki nie wybierzemy nagrania. Klatki demo
mają w rogu oznaczenie „DEMO” i w manifeście tryb = "demo".
"""
import argparse
import hashlib
import json
import os
import subprocess
import sys
import time
import tomllib
from pathlib import Path

import cv2
import numpy as np
from PIL import Image, ImageDraw, ImageFont

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT)); sys.path.insert(0, str(ROOT / "wspolne"))
from wizualizacje.analiza import analizuj, pierwsza_fraza   # noqa: E402
from wizualizacje.czasteczki import PRESETY, W, H           # noqa: E402

FONT = ROOT / "assets" / "fonts" / "Inter-Medium.otf"


def katalog_wyjsciowy(arg):
    if arg:
        return Path(arg)
    cfg = ROOT / "config" / "sciezki.toml"
    if cfg.exists():
        with open(cfg, "rb") as f:
            return Path(os.path.expandvars(tomllib.load(f)["udzial"]["robocze"])) / "nokturn_op9_2_klatki"
    return ROOT / "robocze" / "nokturn_op9_2_klatki"


def audio_demo(out_dir):
    """Własna, prosta fraza testowa w Es-dur 12/8 (NIE melodia Chopina): cichy, rzadki początek,
    gęstszy i głośniejszy środek z ozdobnikami, spokojne zakończenie. Synteza: wspolne/piano_soft.py."""
    from midi_io import write_midi
    PPQ = 480; e = PPQ // 2                      # ósemka
    mel, acc = [], []
    T = lambda osemki: int(round(osemki * e))
    akordy = [(39, [51, 55, 58]), (44, [51, 56, 60]), (46, [50, 53, 58]), (39, [51, 55, 58])] * 2
    for takt, (bas, ak) in enumerate(akordy):
        b0 = 3 + takt * 12                        # 12 ósemek w takcie; 3 ósemki ciszy na starcie
        sila = [0.45, 0.5, 0.6, 0.8, 1.0, 0.95, 0.6, 0.45][takt]
        for g in range(4):                        # rozłożone akordy lewej ręki
            for j, p in enumerate([bas] + ak[:2]):
                acc.append((T(b0 + 3 * g + j), T(b0 + 3 * g + j + 2.6), p, int(34 + 30 * sila)))
        if takt in (0, 1, 6, 7):                  # rzadko: długie dźwięki
            for o, d, p in ((0, 6, 70 + takt % 2 * 2), (6, 5, 67)):
                mel.append((T(b0 + o), T(b0 + o + d), p, int(48 + 30 * sila)))
        else:                                     # gęsto: przebiegi i ozdobniki
            skala = [63, 65, 67, 68, 70, 72, 74, 75, 77, 79]
            for k in range(24 if takt in (3, 4, 5) else 12):
                p = skala[(k * 3 + takt) % len(skala)] + (12 if k % 7 == 3 else 0)
                o = k * (12 / (24 if takt in (3, 4, 5) else 12))
                mel.append((T(b0 + o), T(b0 + o + 0.9), p, int(55 + 40 * sila)))
    mid = out_dir / "demo_fraza_testowa.mid"
    write_midi(str(mid), [("Melodia", 0, mel), ("Akompaniament", 1, acc)], PPQ, [(0, int(60e6 / 66))], (12, 8),
               [(0, "DEMO")], "DEMO - fraza testowa (nie Chopin)")
    raw = out_dir / "demo_audio_raw.wav"; wav = out_dir / "demo_audio.wav"
    env = dict(os.environ, PEDAL="1")
    subprocess.run([sys.executable, str(ROOT / "wspolne" / "piano_soft.py"), str(mid), str(raw), "47"], check=True, env=env)
    subprocess.run(["ffmpeg", "-v", "error", "-y", "-i", str(raw), "-af", "loudnorm=I=-15:TP=-1.5", "-ar", "48000", str(wav)], check=True)
    raw.unlink(missing_ok=True)
    return wav


def do_wav(src, out_dir):
    src = Path(src)
    if src.suffix.lower() == ".wav":
        return src
    dst = out_dir / (src.stem + "_analiza.wav")
    subprocess.run(["ffmpeg", "-v", "error", "-y", "-i", str(src), "-ac", "1", "-ar", "22050", str(dst)], check=True)
    return dst


def znak_demo(img):
    im = Image.fromarray(img)
    d = ImageDraw.Draw(im)
    f = ImageFont.truetype(str(FONT), 22)
    d.text((28, H - 46), "DEMO · syntetyczny sygnał testowy – nie nagranie Chopina", font=f, fill=(255, 255, 255, 150))
    return np.asarray(im)


def main():
    ap = argparse.ArgumentParser()
    g = ap.add_mutually_exclusive_group(required=True)
    g.add_argument("--audio", help="plik nagrania (wav/flac/mp3/oga)")
    g.add_argument("--demo", action="store_true")
    ap.add_argument("--zrodlo", default="", help="wykonawca, źródło i licencja nagrania")
    ap.add_argument("--out")
    ap.add_argument("--seed", type=int, default=20261122)
    ap.add_argument("--presety", nargs="*", default=list(PRESETY))
    a = ap.parse_args()
    out = katalog_wyjsciowy(a.out); out.mkdir(parents=True, exist_ok=True)
    tryb = "demo" if a.demo else "audio"
    wav = audio_demo(out) if a.demo else do_wav(a.audio, out)
    an = analizuj(wav)
    t_pocz = pierwsza_fraza(an)
    t_srod = an.dlugosc / 2
    t_cisza = max(0.0, float(an.ataki[0]) - 0.3) if len(an.ataki) else 0.0
    sha = hashlib.sha256(Path(wav).read_bytes()).hexdigest()
    try:
        commit = subprocess.run(["git", "-C", str(ROOT), "rev-parse", "HEAD"], capture_output=True, text=True).stdout.strip()
    except Exception:
        commit = ""
    manifest = dict(
        utwor="Fryderyk Chopin – Nokturn Es-dur op. 9 nr 2",
        tryb=tryb,
        uwaga=("TRYB DEMO: analiza dotyczy własnej frazy testowej w Es-dur zsyntezowanej z MIDI, "
               "NIE nagrania Chopina. Dokładna synchronizacja z wykonaniem jest zablokowana do czasu "
               "wyboru nagrania o znanym źródle i licencji.") if a.demo else "",
        zrodlo_audio=dict(plik=str(Path(a.audio).name if a.audio else Path(wav).name), sha256=sha,
                          dlugosc_s=round(an.dlugosc, 3), opis=a.zrodlo or ("własna fraza testowa (demo)" if a.demo else "")),
        czasy=dict(poczatek_s=round(t_pocz, 3),
                   poczatek_opis="pierwszy atak powyżej progu głośności + 1,6 s (pierwsza słyszalna fraza)",
                   srodek_s=round(t_srod, 3), srodek_opis="połowa długości nagrania (nie utożsamiamy jej z kulminacją)",
                   kontrola_ciszy_s=round(t_cisza, 3)),
        seed=a.seed, rozdzielczosc=[W, H], commit=commit,
        cechy=dict(poczatek=an.cechy(t_pocz), srodek=an.cechy(t_srod), cisza=an.cechy(t_cisza)),
        presety={},
    )
    pliki = []
    for nazwa in a.presety:
        fn = PRESETY[nazwa]
        manifest["presety"][nazwa] = {}
        for etykieta, t in (("poczatek", t_pocz), ("srodek", t_srod)):
            t0 = time.time()
            c = an.cechy(t)
            rng = np.random.default_rng(a.seed)          # ten sam seed w parze
            kw = dict(analiza=an) if nazwa.startswith("5") else {}
            img, par = fn(c, t, rng, **kw)
            img8 = (np.clip(img, 0, 1) * 255 + 0.5).astype(np.uint8)
            if a.demo:
                img8 = znak_demo(img8)
            p = out / f"{nazwa}_{etykieta}.png"
            cv2.imwrite(str(p), img8[..., ::-1])
            pliki.append(p)
            manifest["presety"][nazwa][etykieta] = dict(plik=p.name, czas_s=round(t, 3), parametry=par,
                                                        render_s=round(time.time() - t0, 1))
            print(f"{p.name}  {time.time() - t0:.1f}s", flush=True)
        # reakcja na ciszę: te same parametry dla chwili ciszy (bez zapisu obrazu)
        _, par0 = fn(an.cechy(t_cisza), t_cisza, np.random.default_rng(a.seed), **(dict(analiza=an) if nazwa.startswith("5") else {}))
        manifest["presety"][nazwa]["kontrola_ciszy"] = dict(czas_s=round(t_cisza, 3), parametry=par0)
    # arkusz porównawczy (dodatek)
    th = []
    for nazwa in a.presety:
        row = [cv2.resize(cv2.imread(str(out / f"{nazwa}_{e}.png")), (640, 360), interpolation=cv2.INTER_AREA)
               for e in ("poczatek", "srodek")]
        th.append(np.hstack(row))
    cv2.imwrite(str(out / "arkusz_porownawczy.png"), np.vstack(th))
    with open(out / "manifest.json", "w", encoding="utf-8") as f:
        json.dump(manifest, f, ensure_ascii=False, indent=2, default=float)
    # kontrola: wymiary i kompletność
    zle = [p.name for p in pliki if Image.open(p).size != (W, H)]
    print("pliki:", len(pliki), "złe wymiary:", zle, "→", out)


if __name__ == "__main__":
    main()
