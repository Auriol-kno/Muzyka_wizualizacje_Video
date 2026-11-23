"""Lokalny serwer ComfyUI dla potoku: sprawdza, uruchamia w tle i czeka na gotowość.

    python -m comfyui.uruchom            # stan; jeśli nie działa – uruchom i poczekaj
    python -m comfyui.uruchom --stan     # tylko stan (wersja, karta, modele)
    python -m comfyui.uruchom --stop     # zatrzymaj serwer uruchomiony przez ten skrypt

Folder instalacji (wersja portable) i adres bierzemy z `config/sciezki.toml`:
    [narzedzia]
    comfyui_url = "http://127.0.0.1:8188"
    comfyui_folder = "D:/.../ComfyUI_windows_portable"

Serwer słucha tylko na 127.0.0.1 (bez dostępu z sieci), bez otwierania przeglądarki.
Dziennik serwera: <robocze>/comfyui/serwer.log. Interfejs: adres z konfiguracji w przeglądarce.
"""
import argparse
import os
import subprocess
import sys
import time
import tomllib
import urllib.parse
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))
from comfyui.klient import Comfy  # noqa: E402


def konfiguracja():
    cfg = ROOT / "config" / "sciezki.toml"
    if not cfg.exists():
        sys.exit("Brak config/sciezki.toml – skopiuj config/sciezki.example.toml i uzupełnij [narzedzia].")
    with open(cfg, "rb") as f:
        return tomllib.load(f)


def folder_comfy(cfg):
    f = cfg.get("narzedzia", {}).get("comfyui_folder")
    if not f:
        sys.exit("Brak [narzedzia] comfyui_folder w config/sciezki.toml (folder ComfyUI_windows_portable).")
    f = Path(f)
    if not (f / "python_embeded" / "python.exe").exists() or not (f / "ComfyUI" / "main.py").exists():
        sys.exit(f"{f} nie wygląda na ComfyUI portable (brak python_embeded/python.exe lub ComfyUI/main.py).")
    return f


def folder_logu(cfg):
    rob = cfg.get("udzial", {}).get("robocze")
    k = Path(rob) / "comfyui" if rob else ROOT / "robocze" / "comfyui"
    k.mkdir(parents=True, exist_ok=True)
    return k


def pokaz_stan(c, st):
    s = st["system"]
    print(f"ComfyUI {s.get('comfyui_version')} działa: {c.url}  (Python {s.get('python_version', '').split()[0]}, "
          f"PyTorch {s.get('pytorch_version')})")
    for d in st.get("devices", []):
        print(f"  karta: {d['name']}  VRAM wolne {d['vram_free'] / 2**30:.1f} / {d['vram_total'] / 2**30:.1f} GB")
    try:
        mod = c.modele("checkpoints")
        print(f"  checkpointy ({len(mod)}): " + (", ".join(mod) if mod else "brak"))
    except OSError:
        pass


def uruchom(cfg, c, czekaj_s=240):
    folder = folder_comfy(cfg)
    u = urllib.parse.urlparse(c.url)
    if u.hostname not in ("127.0.0.1", "localhost"):
        sys.exit(f"comfyui_url = {c.url} nie jest lokalny – ten skrypt uruchamia tylko serwer na tym komputerze.")
    log = folder_logu(cfg) / "serwer.log"
    argumenty = [str(folder / "python_embeded" / "python.exe"), "-s", str(folder / "ComfyUI" / "main.py"),
                 "--windows-standalone-build", "--listen", "127.0.0.1", "--port", str(u.port or 8188),
                 "--disable-auto-launch"]
    # menedżer dodatków wbudowany w ComfyUI ≥ 0.4x (pakiet comfyui_manager z manager_requirements.txt)
    if (folder / "ComfyUI" / "manager_requirements.txt").exists():
        argumenty.append("--enable-manager")
    print("Uruchamiam:", " ".join(argumenty))
    # serwer ma przeżyć okno/terminal, z którego go uruchomiono (odłączony, poza zadaniem nadrzędnym)
    flagi = (subprocess.CREATE_NEW_PROCESS_GROUP | subprocess.DETACHED_PROCESS | subprocess.CREATE_NO_WINDOW
             if os.name == "nt" else 0)
    with open(log, "ab") as f:
        try:
            p = subprocess.Popen(argumenty, cwd=folder, stdout=f, stderr=subprocess.STDOUT, stdin=subprocess.DEVNULL,
                                 creationflags=flagi | (subprocess.CREATE_BREAKAWAY_FROM_JOB if os.name == "nt" else 0))
        except OSError:   # zadanie nadrzędne nie pozwala się odłączyć – uruchom bez tej flagi
            p = subprocess.Popen(argumenty, cwd=folder, stdout=f, stderr=subprocess.STDOUT, stdin=subprocess.DEVNULL,
                                 creationflags=flagi)
    (folder_logu(cfg) / "serwer.pid").write_text(str(p.pid))
    t0 = time.time()
    while time.time() - t0 < czekaj_s:
        if p.poll() is not None:
            sys.exit(f"Serwer zakończył się (kod {p.returncode}). Zobacz dziennik: {log}")
        st = c.dziala()
        if st:
            print(f"Gotowy po {time.time() - t0:.0f} s. Dziennik: {log}")
            return st
        time.sleep(2)
    sys.exit(f"Serwer nie odpowiedział w {czekaj_s} s. Dziennik: {log}")


def zatrzymaj(cfg):
    plik = folder_logu(cfg) / "serwer.pid"
    if not plik.exists():
        sys.exit("Brak serwer.pid – serwer nie był uruchomiony tym skryptem (zamknij jego okno ręcznie).")
    pid = plik.read_text().strip()
    subprocess.run(["taskkill", "/PID", pid, "/T", "/F"] if os.name == "nt" else ["kill", pid], check=False)
    plik.unlink()
    print(f"Zatrzymany (PID {pid}).")


def main():
    ap = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument("--stan", action="store_true", help="tylko pokaż stan, nie uruchamiaj")
    ap.add_argument("--stop", action="store_true", help="zatrzymaj serwer uruchomiony tym skryptem")
    a = ap.parse_args()
    cfg = konfiguracja()
    if a.stop:
        return zatrzymaj(cfg)
    c = Comfy(url=cfg.get("narzedzia", {}).get("comfyui_url"))
    st = c.dziala()
    if not st:
        if a.stan:
            sys.exit(f"ComfyUI nie działa pod {c.url}. Uruchom: python -m comfyui.uruchom")
        st = uruchom(cfg, c)
    pokaz_stan(c, st)


if __name__ == "__main__":
    main()
