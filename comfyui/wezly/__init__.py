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
        n = len([x for x in czasy_s.replace(";", ",").split(",") if x.strip()])
        postep = None
        try:
            import comfy.utils
            pb = comfy.utils.ProgressBar(n)
            licz = {"k": 0}

            def postep(linia):
                if linia.lower().endswith(".png"):
                    licz["k"] += 1
                    pb.update_absolute(licz["k"], n)
        except ImportError:
            pass
        linie = _uruchom([str(ROOT / "skrypty" / "klatki.py"), "--wav", wav, "--preset", preset, "--czasy", czasy_s,
                          "--rozmiar", f"{szerokosc}x{wysokosc}", "--seed", str(seed), "--podpis", podpis,
                          "--wyj", str(wyj)], postep)
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
            "fps": ("FLOAT", {"default": 25.0, "min": 1.0, "max": 60.0, "step": 0.5,
                              "tooltip": "np. 12.5 + RIFE ×2 w ComfyUI = 25 fps w połowie czasu renderu"}),
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
                     "--do", str(do_s), "--fps", f"{fps:g}", "--seed", str(seed), "--podpis", podpis]
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


class MGKontrola:
    """Kontrola jakości gotowego MP4 jak w potoku – np. po interpolacji RIFE / powiększeniu i zapisie przez
    VideoHelperSuite (wejście `pliki` z „Video Combine”) albo dla ścieżki MP4 podanej tekstem."""

    @classmethod
    def INPUT_TYPES(cls):
        return {"required": {}, "optional": {
            "pliki": ("VHS_FILENAMES",),
            "mp4": ("STRING", {"default": "", "forceInput": True}),
        }}

    RETURN_TYPES = ("STRING", "BOOLEAN")
    RETURN_NAMES = ("kontrola", "ok")
    FUNCTION = "sprawdz"
    CATEGORY = KATEGORIA
    OUTPUT_NODE = True

    def sprawdz(self, pliki=None, mp4=""):
        if pliki and not mp4:
            mp4 = next((f for f in reversed(pliki[1]) if str(f).lower().endswith(".mp4")), "")
        if pliki is not None and not mp4:
            # praca partiami (VHS Batch Manager): plik powstaje dopiero po ostatniej partii
            return {"ui": {"text": ["czekam na ostatnią partię…"]}, "result": ("", False)}
        if not mp4 or not Path(mp4).exists():
            raise RuntimeError("brak pliku MP4 do kontroli")
        _uruchom([str(ROOT / "skrypty" / "kontrola.py"), str(mp4)])
        raport = json.loads(Path(mp4).with_suffix(".qc.json").read_text(encoding="utf-8"))["kontrola"]
        tekst = json.dumps(raport, ensure_ascii=False, indent=2)
        werdykt = ("OK" if raport["ok"] else "UWAGA: kontrola nie przeszła") + f" – {Path(mp4).name}"
        return {"ui": {"text": [werdykt + "\n" + tekst]}, "result": (tekst, bool(raport["ok"]))}


class MGPiasek:
    """„Piasek fraktalny”: proceduralny piasek (wydmy, wiry, ziarna) sterowany pomiarem dźwięku z pliku
    (MP4 lub audio). Dźwięk klipu = niezmieniona ścieżka źródła. Render wznawialny (klatki PNG)."""

    @classmethod
    def INPUT_TYPES(cls):
        return {"required": {
            "zrodlo": ("STRING", {"default": "", "tooltip": "pełna ścieżka pliku z dźwiękiem (MP4/WAV)"}),
            "seed": ("INT", {"default": 20261123, "min": 0, "max": 2**31 - 1}),
            "procesy": ("INT", {"default": 4, "min": 1, "max": 32, "tooltip": "wersja 3D: ~2,5 GB RAM na proces"}),
        }}

    RETURN_TYPES = ("STRING", "STRING", "IMAGE")
    RETURN_NAMES = ("mp4", "kontrola", "podglad")
    FUNCTION = "renderuj"
    CATEGORY = KATEGORIA
    OUTPUT_NODE = True

    @classmethod
    def IS_CHANGED(cls, zrodlo, seed, procesy):
        """Zmiana kodu renderera = nowy wynik (ComfyUI inaczej zwróciłby klip z pamięci podręcznej)."""
        pliki = [ROOT / "wizualizacje" / "piasek3d.py", ROOT / "wizualizacje" / "piasek.py",
                 ROOT / "skrypty" / "piasek.py", Path(zrodlo.strip().strip('"'))]
        return hashlib.sha1("|".join(f"{q}:{q.stat().st_mtime_ns}" for q in pliki if q.exists()).encode()).hexdigest()

    def renderuj(self, zrodlo, seed, procesy):
        zr = Path(zrodlo.strip().strip('"'))
        if not zr.exists():
            raise FileNotFoundError(f"brak pliku: {zr}")
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
        linie = _uruchom([str(ROOT / "skrypty" / "piasek.py"), "--zrodlo", str(zr), "--seed", str(seed),
                          "--procesy", str(procesy)], pasek)
        mp4 = next((l.split("→", 1)[1].strip() for l in reversed(linie) if "→" in l and l.strip().endswith(".mp4")), "")
        if not mp4 or not Path(mp4).exists():
            raise RuntimeError("nie znaleziono pliku MP4 w wyjściu renderera")
        kontrola = json.dumps(json.loads(Path(mp4).with_suffix(".qc.json").read_text(encoding="utf-8"))["kontrola"],
                              ensure_ascii=False, indent=2)
        pod = _robocze() / "podglad_piasku"
        shutil.rmtree(pod, ignore_errors=True); pod.mkdir(parents=True)
        dl = json.loads(kontrola)["dlugosc_obrazu_s"]
        for i in range(4):
            subprocess.run(["ffmpeg", "-v", "error", "-y", "-ss", f"{dl * (i + 0.5) / 4:.2f}", "-i", mp4, "-frames:v", "1",
                            str(pod / f"p{i}.png")], env=_env(), check=False)
        pliki = sorted(pod.glob("p*.png"))
        return {"ui": {"text": [mp4]}, "result": (mp4, kontrola, _do_tensora(pliki) if pliki else torch.zeros(1, 64, 64, 3))}


NODE_CLASS_MAPPINGS = {"MGKlatki": MGKlatki, "MGKlip": MGKlip, "MGKontrola": MGKontrola, "MGPiasek": MGPiasek}
NODE_DISPLAY_NAME_MAPPINGS = {"MGKlatki": "Muzyka Graficznie – klatki z dźwięku",
                              "MGKlip": "Muzyka Graficznie – klip MP4 (potok + kontrola)",
                              "MGKontrola": "Muzyka Graficznie – kontrola jakości MP4",
                              "MGPiasek": "Muzyka Graficznie – piasek fraktalny (klip z dźwięku)"}


# ----------------------------------------------------------------------------- stan na żywo (panel)
# Zapisujemy zdarzenia wykonania (który blok liczy, postęp, błędy) i wystawiamy je pod GET /mg/stan,
# żeby panel „przepływ pracy” (mod Claude, comfyui/panel/) mógł rysować bloki bez websocketu.
import threading
import time as _time

_STAN_LOCK = threading.Lock()
_STAN = {"biezace": None, "historia": []}


def _notuj(zdarzenie, dane):
    if not isinstance(dane, dict):
        return
    teraz = _time.time()
    with _STAN_LOCK:
        b = _STAN["biezace"]
        pid = dane.get("prompt_id")
        if zdarzenie == "execution_start":
            _STAN["biezace"] = {"prompt_id": pid, "start": teraz, "wezly": {}, "blad": None}
            return
        if b is None or (pid and pid != b["prompt_id"]):
            return
        w = b["wezly"]
        if zdarzenie == "execution_cached":
            for n in dane.get("nodes", []):
                w[str(n)] = {"stan": "z pamięci"}
        elif zdarzenie == "executing":
            for v in w.values():
                if v.get("stan") == "liczy":
                    v["stan"] = "gotowe"; v["koniec"] = teraz
            n = dane.get("node")
            if n is not None:
                w[str(n)] = {"stan": "liczy", "start": teraz}
        elif zdarzenie == "progress":
            n = str(dane.get("node"))
            w.setdefault(n, {"stan": "liczy", "start": teraz}).update(value=dane.get("value"), max=dane.get("max"))
        elif zdarzenie == "executed":
            n = str(dane.get("node"))
            w.setdefault(n, {})["stan"] = "gotowe"
            tekst = (dane.get("output") or {}).get("text")
            if tekst:
                w[n]["wynik"] = str(tekst[0])[:300]
        elif zdarzenie in ("execution_success", "execution_error", "execution_interrupted"):
            for v in w.values():
                if v.get("stan") == "liczy":
                    v["stan"] = "błąd" if zdarzenie == "execution_error" else "gotowe"
            if zdarzenie == "execution_error":
                b["blad"] = f"{dane.get('node_type')}: {str(dane.get('exception_message', '')).strip()[:300]}"
            b["koniec"] = teraz
            b["wynik"] = {"execution_success": "ok", "execution_error": "błąd",
                          "execution_interrupted": "przerwane"}[zdarzenie]
            _STAN["historia"] = ([{k: b.get(k) for k in ("prompt_id", "start", "koniec", "wynik", "blad")}
                                  | {"wezly": b.get("typy", {})}] + _STAN["historia"])[:10]
            _STAN["ostatnie"] = b
            _STAN["biezace"] = None


def _podepnij_serwer():
    try:
        from aiohttp import web
        from server import PromptServer
    except ImportError:
        return
    srv = getattr(PromptServer, "instance", None)
    if srv is None or getattr(srv, "_mg_podpiety", False):
        return
    oryginal = srv.send_sync

    def send_sync(event, data, sid=None):
        try:
            _notuj(event, data)
        except Exception:  # noqa: BLE001 – panel nie może psuć wykonania
            pass
        return oryginal(event, data, sid)

    srv.send_sync = send_sync
    srv._mg_podpiety = True

    def _bloki(prompt, wezly):
        bloki = []
        for nid, n in sorted(prompt.items(), key=lambda kv: int(kv[0]) if str(kv[0]).isdigit() else 0):
            wej = [str(v[0]) for v in n.get("inputs", {}).values() if isinstance(v, list) and len(v) == 2]
            s = wezly.get(str(nid), {})
            bloki.append({"id": str(nid), "typ": n.get("class_type"),
                          "tytul": (n.get("_meta") or {}).get("title") or NODE_DISPLAY_NAME_MAPPINGS.get(n.get("class_type")) or n.get("class_type"),
                          "wejscia": wej, "stan": s.get("stan", "czeka"), "value": s.get("value"), "max": s.get("max"),
                          "start": s.get("start"), "koniec": s.get("koniec"), "wynik": s.get("wynik")})
        return bloki

    @srv.routes.get("/mg/stan")
    async def mg_stan(_req):
        biegnace, czekajace = srv.prompt_queue.get_current_queue()
        with _STAN_LOCK:
            b = _STAN["biezace"]
            wynik = {"teraz": _time.time(), "w_kolejce": len(czekajace), "historia": list(_STAN["historia"]),
                     "biezace": None, "ostatnie": None}
            if b and biegnace:
                prompt = biegnace[0][2]
                wynik["biezace"] = {"prompt_id": b["prompt_id"], "start": b["start"], "bloki": _bloki(prompt, b["wezly"])}
                b["typy"] = [n.get("class_type") for n in prompt.values()]
            o = _STAN.get("ostatnie")
        if o:
            prompt = None
            try:
                h = srv.prompt_queue.get_history(prompt_id=o["prompt_id"])
                prompt = h[o["prompt_id"]]["prompt"][2]
            except Exception:  # noqa: BLE001
                pass
            if prompt:
                wynik["ostatnie"] = {k: o.get(k) for k in ("prompt_id", "start", "koniec", "wynik", "blad")} | {
                    "bloki": _bloki(prompt, o["wezly"])}
        return web.json_response(wynik)

    @srv.routes.get("/mg/panel")
    async def mg_panel(_req):
        """Panel „przepływ pracy” w przeglądarce: http://127.0.0.1:8188/mg/panel"""
        return web.FileResponse(Path(__file__).with_name("panel.html"), headers={"Cache-Control": "no-store"})


_podepnij_serwer()
