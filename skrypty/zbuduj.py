"""Buduje klip jednego utworu: MIDI → dźwięk fortepianu → render obrazu → MP4 → kontrola jakości.
Działa na Windows, macOS i Linux (wymaga Pythona 3.11+ i ffmpeg w PATH).

  python skrypty/zbuduj.py vivaldi_jesien_allegro            # pełny klip (podgląd 1080p)
  python skrypty/zbuduj.py bach_goldberg_aria --test 30 90   # tylko klatki PNG
  python skrypty/zbuduj.py chopin_walc_a-moll --tylko-audio
"""
import argparse
import os
import shutil
import subprocess
import sys
import tomllib
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]

# opis utworów: plik MIDI, długość klipu [s], silnik brzmienia, pedał
UTWORY = {
    "chopin_walc_a-moll": dict(midi="Chopin_Walc_a-moll_B150.mid", dur=109.0, synth="piano_synth.py", pedal="1",
                               nazwa="Chopin_Walc_a-moll_B150"),
    "bach_goldberg_aria": dict(midi="Bach_Goldberg_Aria_BWV988.mid", dur=195.0, synth="piano_synth.py", pedal="0",
                               nazwa="Bach_Goldberg_Aria"),
    "vivaldi_jesien_allegro": dict(midi="autumn_piano.mid", dur=308.0, synth="piano_soft.py", pedal="0",
                                   nazwa="Vivaldi_Jesien_Allegro"),
}


def sciezki():
    cfg = ROOT / "config" / "sciezki.toml"
    if not cfg.exists():
        cfg = ROOT / "config" / "sciezki.example.toml"
    with open(cfg, "rb") as f:
        c = tomllib.load(f)
    return Path(os.path.expandvars(c["udzial"]["wyniki"])), Path(os.path.expandvars(c["udzial"]["robocze"]))


def run(cmd, **kw):
    print("»", " ".join(map(str, cmd)), flush=True)
    subprocess.run([str(c) for c in cmd], check=True, **kw)


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("utwor", choices=sorted(UTWORY))
    ap.add_argument("--test", nargs="*", type=float, help="sekundy, dla których zapisać klatki PNG")
    ap.add_argument("--tylko-audio", action="store_true")
    ap.add_argument("--res", default="1", help="1 = 1920×1080 (podgląd), 2 = 3840×2160 (4K)")
    ap.add_argument("--segmenty", type=int, default=3)
    a = ap.parse_args()
    u = UTWORY[a.utwor]
    wyniki, robocze = sciezki()
    work = robocze / a.utwor
    work.mkdir(parents=True, exist_ok=True)
    wyniki.mkdir(parents=True, exist_ok=True)
    d = ROOT / "utwory" / a.utwor
    env = dict(os.environ, RES=a.res, DUR=str(u["dur"]), PEDAL=u["pedal"], MIDI=str(d / u["midi"]))
    py = sys.executable
    if a.test:
        run([py, d / "render.py", "--test", *a.test], env=env, cwd=d)
        return
    audio = work / "audio.wav"
    run([py, ROOT / "wspolne" / u["synth"], d / u["midi"], work / "audio_raw.wav", u["dur"]], env=env)
    run(["ffmpeg", "-v", "error", "-y", "-i", work / "audio_raw.wav", "-af", "loudnorm=I=-15:TP=-1.5:LRA=11",
         "-ar", "48000", audio])
    if a.tylko_audio:
        shutil.copy(audio, wyniki / f"{u['nazwa']}.wav")
        return
    nf = int(round(u["dur"] * 30))
    edges = [round(nf * k / a.segmenty) for k in range(a.segmenty + 1)]
    lista = work / "segmenty.txt"
    with open(lista, "w", encoding="utf-8") as f:
        for k in range(a.segmenty):
            seg = work / f"seg{k}.mp4"
            if not (work / f"seg{k}.ok").exists():
                run([py, d / "render.py", "--seg", edges[k], edges[k + 1], seg], env=env, cwd=d)
                (work / f"seg{k}.ok").write_text("ok")
            f.write(f"file '{seg.as_posix()}'\n")
    sufiks = "4K" if a.res == "2" else "podglad"
    out = wyniki / f"{u['nazwa']}_{sufiks}.mp4"
    run(["ffmpeg", "-y", "-v", "error", "-f", "concat", "-safe", "0", "-i", lista, "-i", audio, "-map", "0:v",
         "-map", "1:a", "-c:v", "copy", "-tag:v", "avc1", "-c:a", "aac", "-b:a", "192k", "-ar", "48000", "-ac", "2",
         "-t", u["dur"], "-movflags", "+faststart", out])
    run(["ffprobe", "-v", "error", "-show_entries", "format=duration,size:stream=codec_name,nb_frames,duration",
         "-of", "default=nw=1", out])
    print("gotowe:", out)


if __name__ == "__main__":
    main()
