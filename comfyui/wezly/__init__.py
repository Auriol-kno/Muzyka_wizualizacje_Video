"""Węzły ComfyUI „Muzyka Graficznie”: wizualizacje cząsteczkowe z dźwięku prosto w ComfyUI.

Węzły nie liczą obrazu w Pythonie ComfyUI (brak tam opencv/scipy) – wywołują renderer projektu
(`skrypty/klatki.py`, `skrypty/animacja.py`) Pythonem projektu, więc wynik jest identyczny z potokiem
(ruch z pomiaru nagrania, te same ścieżki kamery, normalizacja głośności, kontrola jakości).

Instalacja: folder `comfyui/wezly` podłączony jako `ComfyUI/custom_nodes/muzyka_graficznie`
(łącze katalogu – patrz comfyui/README.md). Python projektu: [narzedzia] python w config/sciezki.toml.
"""
import hashlib
import json
import os
import re
import shutil
import subprocess
import sys
import tomllib
from pathlib import Path

import numpy as np
import torch
from PIL import Image

ROOT = Path(__file__).resolve().parents[2]
KATEGORIA = "Muzyka Graficznie"
_ZAPAS = ["3_gory_ze_strun", "1_wyspa_poziomic", "2_wstega_iskier", "4_dolina_nokturnu", "5_membrana_bessela",
          "5b_topografia_tory", "5_topografia_dzwieku", "1_cymatyka_zloty_piasek", "2_ocean_harmonicznych",
          "3_fraktalny_ogrod", "4_orbity_rezonansu"]


# ----------------------------------------------------------------------------- konfiguracja
def _cfg():
    p = ROOT / "config" / "sciezki.toml"
    if p.exists():
        with open(p, "rb") as f:
            return tomllib.load(f)
    return {}


def _python():
    py = _cfg().get("narzedzia", {}).get("python")
    if py and Path(py).exists():
        return py
    for kand in ("python", "py"):
        w = shutil.which(kand)
        if w and "python_embeded" not in w:
            return w
    raise RuntimeError("Nie znaleziono Pythona projektu – wpisz [narzedzia] python w config/sciezki.toml")


def _env():
    """Środowisko z pełnym PATH systemu (ffmpeg) i UTF-8 – serwer ComfyUI mógł wystartować z uboższym."""
    env = dict(os.environ, PYTHONIOENCODING="utf-8", PYTHONUTF8="1")
    if os.name == "nt":
        import winreg
        czesci = []
        for klucz, sciezka in ((winreg.HKEY_LOCAL_MACHINE, r"SYSTEM\CurrentControlSet\Control\Session Manager\Environment"),
                               (winreg.HKEY_CURRENT_USER, "Environment")):
            try:
                with winreg.OpenKey(klucz, sciezka) as k:
                    czesci.append(os.path.expandvars(winreg.QueryValueEx(k, "Path")[0]))
            except OSError:
                pass
        env["PATH"] = os.pathsep.join(czesci + [env.get("PATH", "")])
    # Python projektu nie może dziedziczyć ścieżek modułów ComfyUI
    env.pop("PYTHONPATH", None); env.pop("PYTHONHOME", None)
    return env


def _robocze():
    r = _cfg().get("udzial", {}).get("robocze")
    k = (Path(os.path.expandvars(r)) if r else ROOT / "robocze") / "comfyui"
    k.mkdir(parents=True, exist_ok=True)
    return k


def _domyslny_wav():
    z = _cfg().get("udzial", {}).get("zrodla")
    if z:
        wavy = sorted(Path(os.path.expandvars(z)).glob("*.wav"))
        if wavy:
            return wavy[0].name
    return ""


def _sciezka_wav(wav):
    """Pełna ścieżka albo sama nazwa pliku z folderu [udzial] zrodla (workflowy w repo bez ścieżek komputera)."""
    p = Path(wav.strip().strip('"'))
    if not p.is_absolute():
        z = _cfg().get("udzial", {}).get("zrodla")
        if z:
            p = Path(os.path.expandvars(z)) / p
    if not p.exists():
        raise FileNotFoundError(f"brak pliku dźwięku: {p}")
    return str(p)


_PRESETY = None


def _presety():
    global _PRESETY
    if _PRESETY is None:
        try:
            p = subprocess.run([_python(), str(ROOT / "skrypty" / "klatki.py"), "--lista"], capture_output=True,
                               text=True, encoding="utf-8", env=_env(), timeout=120)
            d = json.loads(p.stdout)
            _PRESETY = d["koncepcje_v2"] + d["czasteczki"]
        except Exception as e:  # noqa: BLE001 – węzeł ma się załadować nawet bez Pythona projektu
            _log(f"[Muzyka Graficznie] lista presetów z zapasu ({e})")
            _PRESETY = list(_ZAPAS)
    return _PRESETY


def _do_tensora(pliki):
    obrazy = [np.asarray(Image.open(p).convert("RGB"), dtype=np.float32) / 255.0 for p in pliki]
    return torch.from_numpy(np.stack(obrazy))   # [B, H, W, 3], 0..1 – format IMAGE w ComfyUI


def _log(tekst):
    """Wypis do konsoli ComfyUI; konsola Windows (cp1250) nie zna części znaków (→, ·) – zamieniamy je."""
    try:
        print(tekst, flush=True)
    except UnicodeEncodeError:
        kod = getattr(sys.stdout, "encoding", None) or "ascii"
        print(tekst.encode(kod, errors="replace").decode(kod), flush=True)


def _uruchom(argumenty, postep=None):
    """Uruchamia skrypt projektu, przekazuje wyjście do konsoli ComfyUI, zwraca linie wyjścia."""
    _log("[Muzyka Graficznie] " + " ".join(argumenty))
    p = subprocess.Popen([_python(), *argumenty], cwd=ROOT, env=_env(), stdout=subprocess.PIPE,
                         stderr=subprocess.STDOUT, text=True, encoding="utf-8", errors="replace")
    linie = []
    for linia in p.stdout:
        linia = linia.rstrip()
        linie.append(linia)
        _log("  " + linia)
        if postep:
            postep(linia)
    if p.wait():
        raise RuntimeError("renderer zakończył się błędem:\n" + "\n".join(linie[-25:]))
    return linie


# ----------------------------------------------------------------------------- węzły
class MGKlatki:
    """Klatki wizualizacji w wybranych chwilach utworu → IMAGE (podgląd, wejście do img2img SDXL)."""

    @classmethod
    def INPUT_TYPES(cls):
        return {"required": {
            "wav": ("STRING", {"default": _domyslny_wav()}),
            "preset": (_presety(), {"default": "3_gory_ze_strun"}),
            "czasy_s": ("STRING", {"default": "62, 211", "tooltip": "chwile utworu w sekundach, po przecinku"}),
            "szerokosc": ("INT", {"default": 1280, "min": 256, "max": 3840, "step": 8}),
            "wysokosc": ("INT", {"default": 720, "min": 144, "max": 2160, "step": 8}),
            "seed": ("INT", {"default": 20261122, "min": 0, "max": 2**31 - 1}),
            "podpis": ("STRING", {"default": "", "multiline": True}),
        }}

    RETURN_TYPES = ("IMAGE",)
    RETURN_NAMES = ("klatki",)
    FUNCTION = "renderuj"
    CATEGORY = KATEGORIA

    def renderuj(self, wav, preset, czasy_s, szerokosc, wysokosc, seed, podpis):
        wav = _sciezka_wav(wav)
        klucz = hashlib.sha1(json.dumps([wav, preset, czasy_s, szerokosc, wysokosc, seed, podpis]).encode()).hexdigest()[:12]
        wyj = _robocze() / "klatki" / klucz
        if wyj.exists():
            shutil.rmtree(wyj)
        linie = _uruchom([str(ROOT / "skrypty" / "klatki.py"), "--wav", wav, "--preset", preset, "--czasy", czasy_s,
                          "--rozmiar", f"{szerokosc}x{wysokosc}", "--seed", str(seed), "--podpis", podpis,
                          "--wyj", str(wyj)])
        pliki = [l for l in linie if l.lower().endswith(".png") and Path(l).exists()]
        if not pliki:
            raise RuntimeError("renderer nie zwrócił klatek")
        return (_do_tensora(pliki),)


class MGKlip:
    """Cały klip (albo fragment) jak w potoku: dźwięk −15 LUFS, H.264 + AAC, kontrola jakości.
    Zwraca ścieżkę MP4, raport kontroli i kilka klatek z gotowego pliku do podglądu."""

    @classmethod
    def INPUT_TYPES(cls):
        return {"required": {
            "wav": ("STRING", {"default": _domyslny_wav()}),
            "preset": (_presety(), {"default": "3_gory_ze_strun"}),
            "od_s": ("FLOAT", {"default": 0.0, "min": 0.0, "max": 36000.0, "step": 0.5}),
            "do_s": ("FLOAT", {"default": 10.0, "min": 0.0, "max": 36000.0, "step": 0.5,
                               "tooltip": "0 = do końca utworu"}),
            "fps": ("INT", {"default": 25, "min": 1, "max": 60}),
            "rozmiar": (["1280x720", "1920x1080", "3840x2160"],),
            "seed": ("INT", {"default": 20261122, "min": 0, "max": 2**31 - 1}),
            "podpis": ("STRING", {"default": "", "multiline": True}),
        }}

    RETURN_TYPES = ("STRING", "STRING", "IMAGE")
    RETURN_NAMES = ("mp4", "kontrola", "podglad")
    FUNCTION = "renderuj"
    CATEGORY = KATEGORIA
    OUTPUT_NODE = True

    def renderuj(self, wav, preset, od_s, do_s, fps, rozmiar, seed, podpis):
        wav = _sciezka_wav(wav)
        argumenty = [str(ROOT / "skrypty" / "animacja.py"), "--wav", wav, "--preset", preset, "--od", str(od_s),
                     "--do", str(do_s), "--fps", str(fps), "--seed", str(seed), "--podpis", podpis]
        if rozmiar != "1920x1080":
            argumenty += ["--rozmiar", rozmiar]
        pasek = None
        try:
            import comfy.utils
            stan = {"pb": None}

            def pasek(linia):
                m = re.search(r"klatka (\d+)/(\d+)", linia)
                if m:
                    k, n = int(m.group(1)), int(m.group(2))
                    if stan["pb"] is None:
                        stan["pb"] = comfy.utils.ProgressBar(n)
                    stan["pb"].update_absolute(k, n)
        except ImportError:
            pass
        linie = _uruchom(argumenty, pasek)
        mp4 = next((l.split("→", 1)[1].strip() for l in reversed(linie) if "→" in l and l.strip().endswith(".mp4")), "")
        if not mp4 or not Path(mp4).exists():
            raise RuntimeError("nie znaleziono pliku MP4 w wyjściu renderera")
        qc_plik = Path(mp4).with_suffix(".qc.json")
        kontrola = qc_plik.read_text(encoding="utf-8") if qc_plik.exists() else ""
        # podgląd: 4 klatki z gotowego pliku (to, co naprawdę jest w MP4)
        pod = _robocze() / "podglad_klipu"
        if pod.exists():
            shutil.rmtree(pod)
        pod.mkdir(parents=True)
        dl = json.loads(kontrola)["kontrola"]["dlugosc_obrazu_s"] if kontrola else 10.0
        for i in range(4):
            subprocess.run(["ffmpeg", "-v", "error", "-y", "-ss", f"{dl * (i + 0.5) / 4:.2f}", "-i", mp4, "-frames:v", "1",
                            str(pod / f"p{i}.png")], env=_env(), check=False)
        pliki = sorted(pod.glob("p*.png"))
        podglad = _do_tensora(pliki) if pliki else torch.zeros(1, 64, 64, 3)
        return {"ui": {"text": [mp4]}, "result": (mp4, kontrola, podglad)}


NODE_CLASS_MAPPINGS = {"MGKlatki": MGKlatki, "MGKlip": MGKlip}
NODE_DISPLAY_NAME_MAPPINGS = {"MGKlatki": "Muzyka Graficznie – klatki z dźwięku",
                              "MGKlip": "Muzyka Graficznie – klip MP4 (potok + kontrola)"}
