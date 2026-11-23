"""Animacja z pliku dźwiękowego: WAV → analiza → klatki (preset cząsteczkowy) → MP4 + kontrola jakości.

  python skrypty/animacja.py --wav nagranie.wav --preset 5b_topografia_tory \
      --podpis "Fryderyk Chopin – Nokturn Es-dur op. 9 nr 2\\nwyk. Martha Goldstein · CC BY-SA 2.0"
  python skrypty/animacja.py --wav nagranie.wav --od 60 --do 70      # szybki test fragmentu

Standard serii (AGENTS.md): H.264 + AAC 48 kHz, 30 fps, 1920×1080, −15 LUFS, szczyt −1,5 dBTP.
Każda klatka to funkcja pomiaru dźwięku w chwili t = od + i/fps (ten sam plik co ścieżka dźwiękowa),
stały seed → ten sam teren w każdej klatce, zmienia się tylko to, co wynika z dźwięku.
"""
import argparse
import json
import multiprocessing as mp
import os
import re
import subprocess
import sys
import time
import tomllib
from pathlib import Path

import numpy as np

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))

FPS = 30


# ----------------------------------------------------------------------------- ścieżki
def sciezki():
    cfg = ROOT / "config" / "sciezki.toml"
    if cfg.exists():
        with open(cfg, "rb") as f:
            u = tomllib.load(f)["udzial"]
        return Path(os.path.expandvars(u["wyniki"])), Path(os.path.expandvars(u["robocze"]))
    return ROOT / "wyniki", ROOT / "robocze"


def ff(*args, **kw):
    return subprocess.run(["ffmpeg", "-hide_banner", "-nostdin", *map(str, args)], capture_output=True, text=True,
                          encoding="utf-8", errors="replace", **kw)


# ----------------------------------------------------------------------------- dźwięk
def przygotuj_dzwiek(wav, cel, od, do):
    """Dwuprzebiegowa normalizacja do −15 LUFS / −1,5 dBTP, 48 kHz (fragment od–do, jeśli podany)."""
    ciecie = ["-ss", f"{od:.3f}", "-to", f"{do:.3f}"] if do else (["-ss", f"{od:.3f}"] if od else [])
    p = ff(*ciecie, "-i", wav, "-af", "loudnorm=I=-15:TP=-1.5:LRA=11:print_format=json", "-f", "null", "-")
    m = json.loads(re.findall(r"\{[^{}]*\"input_i\"[^{}]*\}", p.stderr)[-1])
    filtr = (f"loudnorm=I=-15:TP=-1.5:LRA=11:measured_I={m['input_i']}:measured_TP={m['input_tp']}:"
             f"measured_LRA={m['input_lra']}:measured_thresh={m['input_thresh']}:offset={m['target_offset']}:"
             f"linear=true:print_format=json")
    p = ff("-y", *ciecie, "-i", wav, "-af", filtr, "-ar", "48000", "-c:a", "pcm_s24le", cel)
    if p.returncode:
        raise RuntimeError(p.stderr[-2000:])
    wynik = json.loads(re.findall(r"\{[^{}]*\"output_i\"[^{}]*\}", p.stderr)[-1])
    return dict(wejscie_lufs=float(m["input_i"]), wejscie_tp=float(m["input_tp"]),
                tryb=wynik.get("normalization_type"), wyjscie_lufs=float(wynik["output_i"]),
                wyjscie_tp=float(wynik["output_tp"]))


# ----------------------------------------------------------------------------- render (procesy)
_S = {}


def _init(wav, preset, seed, podpis, od):
    import cv2
    cv2.setNumThreads(1)
    from wizualizacje.analiza import analizuj
    from wizualizacje.czasteczki import PRESETY, W, H
    _S.update(an=analizuj(wav), fn=PRESETY[preset], seed=seed, od=od, W=W, H=H,
              z_analiza=preset.startswith("5"), warstwa=_warstwa_podpisu(podpis, W, H) if podpis else None)


def _warstwa_podpisu(tekst, W, H, rozmiar=24, margines=28):
    """Podpis w prawym dolnym rogu jako (RGB, alfa) – liczony raz, nakładany na każdą klatkę."""
    from PIL import Image, ImageDraw, ImageFont
    font = ROOT / "assets" / "fonts" / "Inter-Medium.otf"
    im = Image.new("RGBA", (W, H), (0, 0, 0, 0))
    d = ImageDraw.Draw(im)
    linie = tekst.replace("\\n", "\n").split("\n")
    y = H - margines
    for i, linia in enumerate(reversed(linie)):
        f = ImageFont.truetype(str(font), rozmiar if i == len(linie) - 1 else int(rozmiar * 0.75))
        x0, y0, x1, y1 = d.textbbox((0, 0), linia, font=f)
        y -= (y1 - y0) + 8
        d.text((W - margines - (x1 - x0), y - y0), linia, font=f, fill=(255, 255, 255, 190))
    a = np.asarray(im).astype(np.float32) / 255
    return a[..., :3], a[..., 3:]


def _klatka(i):
    s = _S
    t = s["od"] + i / FPS
    kw = dict(analiza=s["an"]) if s["z_analiza"] else {}
    img, _ = s["fn"](s["an"].cechy(t), t, np.random.default_rng(s["seed"]), **kw)
    img = np.clip(img, 0, 1)
    if s["warstwa"] is not None:
        rgb, alfa = s["warstwa"]
        img = img * (1 - alfa) + rgb * alfa
    return i, (img * 255 + 0.5).astype(np.uint8).tobytes()


# ----------------------------------------------------------------------------- kontrola jakości
def kontrola(mp4, oczekiwana_s):
    pr = subprocess.run(["ffprobe", "-v", "error", "-show_entries", "stream=codec_type,codec_name,duration,width,height,"
                         "r_frame_rate,sample_rate,nb_frames", "-of", "json", str(mp4)], capture_output=True, text=True)
    st = {s["codec_type"]: s for s in json.loads(pr.stdout)["streams"]}
    v, a = st["video"], st["audio"]
    dv, da = float(v["duration"]), float(a["duration"])
    p = ff("-i", mp4, "-vf", "blackdetect=d=0.1:pix_th=0.10,signalstats,metadata=print:key=lavfi.signalstats.YAVG",
           "-af", "ebur128=peak=true", "-f", "null", "-")
    yavg = np.array([float(x) for x in re.findall(r"lavfi\.signalstats\.YAVG=([\d.]+)", p.stdout + p.stderr)])
    czarne = re.findall(r"black_start:([\d.]+) black_end:([\d.]+)", p.stderr)
    lufs = re.findall(r"I:\s+(-?[\d.]+) LUFS", p.stderr)
    tp = re.findall(r"Peak:\s+(-?[\d.]+) dBFS", p.stderr)
    skok = float(np.abs(np.diff(yavg)).max()) if len(yavg) > 1 else 0.0
    w = dict(
        wideo=f"{v['codec_name']} {v['width']}x{v['height']} {v['r_frame_rate']} fps, {v.get('nb_frames')} klatek",
        dzwiek=f"{a['codec_name']} {a['sample_rate']} Hz",
        dlugosc_obrazu_s=round(dv, 3), dlugosc_dzwieku_s=round(da, 3), roznica_s=round(abs(dv - da), 3),
        czarne_odcinki=[(float(x), float(y)) for x, y in czarne],
        jasnosc_srednia=round(float(yavg.mean()), 1) if len(yavg) else None,
        najwiekszy_skok_jasnosci=round(skok, 2),
        glosnosc_lufs=float(lufs[-1]) if lufs else None, szczyt_dbtp=float(tp[-1]) if tp else None,
    )
    w["ok"] = bool(w["roznica_s"] <= 1 / FPS + 0.03 and not czarne and skok < 12
                   and w["glosnosc_lufs"] is not None and abs(w["glosnosc_lufs"] + 15) <= 1.0
                   and w["szczyt_dbtp"] is not None and w["szczyt_dbtp"] <= -1.0
                   and v["codec_name"] == "h264" and a["codec_name"] == "aac" and a["sample_rate"] == "48000"
                   and abs(dv - oczekiwana_s) <= 0.1)
    return w


# ----------------------------------------------------------------------------- main
def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--wav", required=True)
    ap.add_argument("--preset", default="5b_topografia_tory")
    ap.add_argument("--podpis", default="")
    ap.add_argument("--od", type=float, default=0.0, help="początek fragmentu [s]")
    ap.add_argument("--do", type=float, default=0.0, help="koniec fragmentu [s] (0 = do końca)")
    ap.add_argument("--seed", type=int, default=20261122)
    ap.add_argument("--procesy", type=int, default=max(1, (os.cpu_count() or 2) // 2))
    ap.add_argument("--crf", type=int, default=18)
    ap.add_argument("--out", help="plik MP4 (domyślnie w folderze wyniki z config/sciezki.toml)")
    a = ap.parse_args()

    from wizualizacje.analiza import analizuj
    from wizualizacje.czasteczki import PRESETY, W, H
    if a.preset not in PRESETY:
        sys.exit(f"nieznany preset {a.preset}; dostępne: {', '.join(PRESETY)}")
    wav = Path(a.wav)
    wyniki, robocze = sciezki()
    nazwa = f"{wav.stem[:60]}_{a.preset}" + (f"_{a.od:g}-{a.do:g}s" if a.do else "")
    out = Path(a.out) if a.out else wyniki / f"{nazwa}.mp4"
    out.parent.mkdir(parents=True, exist_ok=True)
    rob = robocze / "animacja"; rob.mkdir(parents=True, exist_ok=True)

    t0 = time.time()
    dl_calosci = analizuj(wav).dlugosc
    do = a.do or dl_calosci
    dlugosc = do - a.od
    n = int(round(dlugosc * FPS))
    audio = rob / f"{nazwa}_audio48k.wav"
    gl = przygotuj_dzwiek(wav, audio, a.od, a.do)
    print(f"dźwięk: {gl['wejscie_lufs']:.1f} → {gl['wyjscie_lufs']:.1f} LUFS, szczyt {gl['wyjscie_tp']:.1f} dBTP "
          f"({gl['tryb']}); klatek {n} ({dlugosc:.1f} s), procesy {a.procesy}", flush=True)

    enc = subprocess.Popen(
        ["ffmpeg", "-hide_banner", "-loglevel", "error", "-y", "-f", "rawvideo", "-pix_fmt", "rgb24",
         "-s", f"{W}x{H}", "-r", str(FPS), "-i", "-", "-i", str(audio), "-map", "0:v", "-map", "1:a",
         "-c:v", "libx264", "-preset", "medium", "-crf", str(a.crf), "-pix_fmt", "yuv420p", "-r", str(FPS),
         "-c:a", "aac", "-b:a", "256k", "-ar", "48000", "-shortest", "-movflags", "+faststart", str(out)],
        stdin=subprocess.PIPE)
    ctx = mp.get_context("spawn")
    with ctx.Pool(a.procesy, initializer=_init, initargs=(str(wav), a.preset, a.seed, a.podpis, a.od)) as pool:
        t1 = time.time()
        for k, (i, dane) in enumerate(pool.imap(_klatka, range(n), chunksize=2), 1):
            enc.stdin.write(dane)
            if k % 30 == 0 or k == n:
                el = time.time() - t1
                print(f"  klatka {k}/{n}  {el / k:.2f} s/kl.  zostało ~{(n - k) * el / k / 60:.0f} min", flush=True)
    enc.stdin.close()
    if enc.wait():
        sys.exit("ffmpeg: błąd kodowania")

    qc = kontrola(out, n / FPS)
    raport = dict(plik=str(out), wav=str(wav), preset=a.preset, seed=a.seed, od_s=a.od, do_s=do, klatki=n,
                  podpis=a.podpis, glosnosc=gl, kontrola=qc, czas_renderu_min=round((time.time() - t0) / 60, 1))
    with open(out.with_suffix(".qc.json"), "w", encoding="utf-8") as f:
        json.dump(raport, f, ensure_ascii=False, indent=2)
    print(json.dumps(qc, ensure_ascii=False, indent=2))
    print(("OK" if qc["ok"] else "UWAGA: kontrola nie przeszła") + f" → {out}")


if __name__ == "__main__":
    main()
