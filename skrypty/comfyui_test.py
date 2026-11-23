"""Test ComfyUI: czy serwer działa, jakie są modele, ile trwa jedno tło SDXL na tej karcie.

  python skrypty/comfyui_test.py [--out folder] [--prompt "..."]
"""
import argparse
import sys
import time
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))
from comfyui.klient import Comfy                       # noqa: E402
from comfyui.workflowy import MODEL_DOMYSLNY, tlo_sdxl  # noqa: E402


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--out", default=str(ROOT / "robocze" / "comfyui_test"))
    ap.add_argument("--prompt", default="abstract night landscape of fine glowing sand dunes, deep navy blue, "
                                        "soft rose light, minimal, elegant, cinematic, 8k, highly detailed texture")
    ap.add_argument("--seed", type=int, default=20261122)
    a = ap.parse_args()

    c = Comfy()
    st = c.dziala()
    if not st:
        sys.exit(f"ComfyUI nie odpowiada pod {c.url} – uruchom run_nvidia_gpu.bat")
    dev = st["devices"][0]
    print(f"ComfyUI {st['system'].get('comfyui_version', '?')} · {dev['name']} · "
          f"VRAM wolne {dev['vram_free'] / 2**30:.1f}/{dev['vram_total'] / 2**30:.1f} GB")
    modele = c.modele()
    print("checkpointy:", modele)
    if MODEL_DOMYSLNY not in modele:
        sys.exit(f"brak modelu {MODEL_DOMYSLNY}")

    for proba in (1, 2):   # pierwsza z ładowaniem modelu, druga – czysty czas generowania
        t0 = time.time()
        pliki = c.generuj(tlo_sdxl(a.prompt, a.seed + proba), Path(a.out), prefiks=f"proba{proba}_")
        print(f"próba {proba}: {time.time() - t0:.1f} s → {pliki[0]}")


if __name__ == "__main__":
    main()
