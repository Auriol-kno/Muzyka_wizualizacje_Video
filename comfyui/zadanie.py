"""Jedno polecenie: workflow „Muzyka Graficznie” → kolejka ComfyUI → gotowy klip z datą w nazwie + kontrola.

    python -m comfyui.zadanie plynna --od 205 --do 215
    python -m comfyui.zadanie ostrzejsza --mp4 "D:/.../klip.mp4"
    python -m comfyui.zadanie klip --od 0 --do 0 --preset 3_gory_ze_strun
    python -m comfyui.zadanie --lista

Czeka na koniec (także na kolejne partie VideoHelperSuite), sam nic nie wypisuje poza krótkim postępem
co minutę i podsumowaniem na końcu – oszczędnie dla asystenta, który tylko czyta wynik.
Gotowy MP4 (i raport `.qc.json`) kopiowany do `<wyniki>/klipy/RRRR-MM-DD_GG-MM_<nazwa>.mp4`, gdzie data
i godzina to chwila utworzenia klipu na tym komputerze. Ten folder wysyłamy na Dysk Google.
"""
import argparse
import json
import os
import shutil
import sys
import time
import tomllib
from datetime import datetime
from pathlib import Path

from comfyui import workflowy as w
from comfyui.klient import ROOT, Comfy

WORKFLOWY = {
    "podglad": w.wizualizacja_podglad,
    "klip": w.wizualizacja_klip,
    "plynna": w.wizualizacja_plynna,
    "ostrzejsza": w.wizualizacja_ostrzejsza,
}


def folder_klipow():
    cfg = ROOT / "config" / "sciezki.toml"
    wyniki = None
    if cfg.exists():
        with open(cfg, "rb") as f:
            wyniki = tomllib.load(f).get("udzial", {}).get("wyniki")
    k = (Path(os.path.expandvars(wyniki)) if wyniki else ROOT / "wyniki") / "klipy"
    k.mkdir(parents=True, exist_ok=True)
    return k


def kopia_z_data(mp4, nazwa=None):
    """Kopia do <wyniki>/klipy z datą i godziną utworzenia pliku w nazwie (+ raport kontroli)."""
    mp4 = Path(mp4)
    st = mp4.stat()
    t = datetime.fromtimestamp(getattr(st, "st_birthtime", None) or st.st_ctime)
    cel = folder_klipow() / f"{t:%Y-%m-%d_%H-%M}_{nazwa or mp4.stem}.mp4"
    shutil.copy2(mp4, cel)
    qc = mp4.with_suffix(".qc.json")
    if qc.exists():
        shutil.copy2(qc, cel.with_suffix(".qc.json"))
    # opcjonalnie: folder synchronizowany przez Dysk Google na komputer ([udzial] dysk_google)
    dysk = _cfg_udzial().get("dysk_google")
    if dysk and Path(os.path.expandvars(dysk)).is_dir():
        shutil.copy2(cel, Path(os.path.expandvars(dysk)) / cel.name)
    return cel


def _cfg_udzial():
    cfg = ROOT / "config" / "sciezki.toml"
    if cfg.exists():
        with open(cfg, "rb") as f:
            return tomllib.load(f).get("udzial", {})
    return {}


def _czekaj_na_kolejke(c, t0, co=10):
    """Czeka, aż kolejka będzie pusta (VHS dokłada kolejne partie jako nowe zadania)."""
    ostatni = 0.0
    while True:
        q = json.loads(c._get("/queue"))
        n = len(q["queue_running"]) + len(q["queue_pending"])
        if n == 0:
            return
        if time.time() - ostatni > 60:
            print(f"  … {time.time() - t0:.0f} s, w kolejce {n}", flush=True)
            ostatni = time.time()
        time.sleep(co)


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("workflow", nargs="?", choices=list(WORKFLOWY))
    ap.add_argument("--lista", action="store_true")
    ap.add_argument("--od", type=float)
    ap.add_argument("--do", type=float)
    ap.add_argument("--preset")
    ap.add_argument("--mp4", help="ostrzejsza: gotowy plik zamiast renderu")
    ap.add_argument("--nazwa", help="nazwa kopii (bez daty); domyślnie z pliku")
    a = ap.parse_args()
    if a.lista or not a.workflow:
        for k, f in WORKFLOWY.items():
            print(f"{k:12s} {(f.__doc__ or '').strip().splitlines()[0]}")
        return
    kw = {k: v for k, v in dict(od=a.od, do=a.do, preset=a.preset, mp4=a.mp4).items() if v is not None}
    wf = WORKFLOWY[a.workflow](**kw)
    c = Comfy(timeout=24 * 3600)
    if not c.dziala():
        sys.exit("ComfyUI nie działa – python -m comfyui.uruchom")
    t0 = time.time()
    start = set(json.loads(c._get("/history?max_items=200")))
    pid = c.wyslij(wf)
    print(f"{a.workflow}: zadanie {pid}", flush=True)
    _czekaj_na_kolejke(c, t0)
    historia = {k: v for k, v in json.loads(c._get("/history?max_items=200")).items() if k not in start}
    bledy, mp4, raport = [], None, None
    for h in sorted(historia.values(), key=lambda h: h.get("status", {}).get("messages", [[0, {"timestamp": 0}]])[0][1].get("timestamp", 0)):
        for m in h.get("status", {}).get("messages", []):
            if m[0] == "execution_error":
                bledy.append(f"{m[1].get('node_type')}: {m[1].get('exception_message', '').strip()}")
        for o in h.get("outputs", {}).values():
            for g in o.get("gifs", []):
                if g.get("fullpath", "").endswith(".mp4"):
                    mp4 = g["fullpath"]
            for tekst in o.get("text", []):
                if tekst.strip().endswith(".mp4") and Path(tekst.strip()).exists() and not mp4:
                    mp4 = tekst.strip()
                if tekst.startswith(("OK", "UWAGA")):
                    raport = tekst
    wynik = dict(workflow=a.workflow, czas_s=round(time.time() - t0), bledy=bledy)
    if mp4:
        wynik["plik"] = mp4
        wynik["kopia"] = str(kopia_z_data(mp4, a.nazwa))
        qc = Path(mp4).with_suffix(".qc.json")
        if qc.exists():
            k = json.loads(qc.read_text(encoding="utf-8"))["kontrola"]
            wynik["kontrola"] = {x: k[x] for x in ("ok", "dlugosc_obrazu_s", "dlugosc_dzwieku_s", "czarne_odcinki",
                                                   "najwiekszy_skok_jasnosci", "glosnosc_lufs", "szczyt_dbtp", "wideo")}
    elif raport:
        wynik["kontrola"] = raport.splitlines()[0]
    print(json.dumps(wynik, ensure_ascii=False, indent=1))
    sys.exit(1 if bledy and not mp4 else 0)


if __name__ == "__main__":
    main()
