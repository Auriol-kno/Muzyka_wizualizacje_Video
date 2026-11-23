"""Klient API ComfyUI (tylko biblioteka standardowa).

Adres serwera bierzemy z `config/sciezki.toml` → [narzedzia] comfyui_url (domyślnie http://127.0.0.1:8188).
Serwer uruchamia właściciel: `run_nvidia_gpu.bat` w folderze ComfyUI (patrz comfyui/README.md).

    from comfyui.klient import Comfy
    c = Comfy()
    pliki = c.generuj(workflow_dict, Path("wyjscie"))   # workflow w formacie API (Save → API Format)
"""
import json
import time
import tomllib
import urllib.error
import urllib.parse
import urllib.request
import uuid
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]


def adres_z_konfiguracji():
    cfg = ROOT / "config" / "sciezki.toml"
    if cfg.exists():
        with open(cfg, "rb") as f:
            return tomllib.load(f).get("narzedzia", {}).get("comfyui_url", "http://127.0.0.1:8188")
    return "http://127.0.0.1:8188"


class Comfy:
    def __init__(self, url=None, timeout=1800):
        self.url = (url or adres_z_konfiguracji()).rstrip("/")
        self.timeout = timeout
        self.klient_id = uuid.uuid4().hex

    # --- niskopoziomowe
    def _get(self, sciezka):
        with urllib.request.urlopen(self.url + sciezka, timeout=30) as r:
            return r.read()

    def _post(self, sciezka, dane):
        req = urllib.request.Request(self.url + sciezka, data=json.dumps(dane).encode(),
                                     headers={"Content-Type": "application/json"})
        try:
            with urllib.request.urlopen(req, timeout=30) as r:
                return json.loads(r.read())
        except urllib.error.HTTPError as e:   # ComfyUI zwraca opis błędu walidacji w treści
            raise RuntimeError(f"ComfyUI odrzucił workflow: {e.read().decode(errors='replace')}") from None

    # --- publiczne
    def dziala(self):
        try:
            return json.loads(self._get("/system_stats"))
        except OSError:
            return None

    def modele(self, typ="checkpoints"):
        return json.loads(self._get(f"/models/{typ}"))

    def wyslij(self, workflow):
        return self._post("/prompt", {"prompt": workflow, "client_id": self.klient_id})["prompt_id"]

    def czekaj(self, prompt_id, co=1.0):
        t0 = time.time()
        while time.time() - t0 < self.timeout:
            h = json.loads(self._get(f"/history/{prompt_id}"))
            if prompt_id in h:
                st = h[prompt_id].get("status", {})
                if st.get("status_str") == "error":
                    raise RuntimeError(f"błąd wykonania w ComfyUI: {st.get('messages')}")
                return h[prompt_id]
            time.sleep(co)
        raise TimeoutError(f"ComfyUI nie skończył w {self.timeout} s")

    def pobierz(self, wynik, katalog, prefiks=""):
        katalog = Path(katalog); katalog.mkdir(parents=True, exist_ok=True)
        pliki = []
        for wezel in wynik.get("outputs", {}).values():
            for img in wezel.get("images", []):
                q = urllib.parse.urlencode({"filename": img["filename"], "subfolder": img.get("subfolder", ""),
                                            "type": img.get("type", "output")})
                cel = katalog / f"{prefiks}{img['filename']}"
                cel.write_bytes(self._get(f"/view?{q}"))
                pliki.append(cel)
        return pliki

    def wgraj_obraz(self, plik):
        """Wysyła obraz do folderu input/ ComfyUI (dla img2img). Zwraca nazwę do węzła LoadImage."""
        plik = Path(plik)
        granica = uuid.uuid4().hex
        tresc = (f"--{granica}\r\nContent-Disposition: form-data; name=\"image\"; filename=\"{plik.name}\"\r\n"
                 f"Content-Type: image/png\r\n\r\n").encode() + plik.read_bytes() + \
                f"\r\n--{granica}\r\nContent-Disposition: form-data; name=\"overwrite\"\r\n\r\ntrue\r\n--{granica}--\r\n".encode()
        req = urllib.request.Request(self.url + "/upload/image", data=tresc,
                                     headers={"Content-Type": f"multipart/form-data; boundary={granica}"})
        with urllib.request.urlopen(req, timeout=60) as r:
            return json.loads(r.read())["name"]

    def generuj(self, workflow, katalog, prefiks=""):
        return self.pobierz(self.czekaj(self.wyslij(workflow)), katalog, prefiks)
