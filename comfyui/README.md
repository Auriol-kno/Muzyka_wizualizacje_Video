# ComfyUI – praca lokalna

Cel: tła, tekstury i stylizacja klatek (SDXL), które wchodzą do renderu jako warstwy pod cząsteczkami.
Wszystko działa na tym komputerze (GTX 1060 6 GB), serwer słucha tylko na `127.0.0.1`.

## Dwie instalacje – do czego która

| | ComfyUI portable | Comfy Desktop |
|---|---|---|
| Rola | serwer potoku (skrypty, API) | ręczna praca w interfejsie |
| Adres | `http://127.0.0.1:8188` | `http://127.0.0.1:8189` (okno aplikacji) |
| Modele | własne `ComfyUI/models` + modele Desktop (przez `extra_model_paths.yaml`) | `Comfy-Desktop/ComfyUI-Shared/models` |

Obie dzielą jedną kartę 6 GB: przy dłuższym generowaniu w potoku zamknij Desktop (albo odwrotnie).

## Konfiguracja (raz)

1. W `config/sciezki.toml` → `[narzedzia]`:
   ```toml
   comfyui_url = "http://127.0.0.1:8188"
   comfyui_folder = "D:/AI/ComfyUI_windows_portable_nvidia/ComfyUI_windows_portable"
   ```
2. Modele z Comfy Desktop widoczne w portable: skopiuj `comfyui/extra_model_paths.example.yaml` jako
   `ComfyUI/extra_model_paths.yaml` w folderze portable i popraw `base_path`.
   Zapisz plik **bez BOM** (UTF-8) – ComfyUI 0.3.9 inaczej nie startuje.
3. Modele SDXL w `ComfyUI/models/checkpoints` (obecnie `juggernautXL_v9Rdphoto2Lightning`).
   Licencję modelu sprawdzamy przed użyciem obrazu w klipie na YouTube.

## Na co dzień

```powershell
python -m comfyui.uruchom          # stan; jeśli serwer nie działa – uruchom w tle i poczekaj (~45 s)
python -m comfyui.uruchom --stan   # tylko stan: wersja, karta, VRAM, checkpointy
python -m comfyui.uruchom --stop   # zatrzymaj serwer uruchomiony tym skryptem
python -m comfyui.workflowy        # zapisz workflowy do comfyui/workflows/*.json
```

Dziennik serwera: `<robocze>/comfyui/serwer.log`.
Workflowy z `comfyui/workflows/` można otworzyć w interfejsie (przeciągnij plik na okno) i dostroić ręcznie.

## Z Pythona

```python
from comfyui.klient import Comfy
from comfyui.workflowy import tlo_sdxl
Comfy().generuj(tlo_sdxl("night sky over misty mountains, navy and gold", seed=7), "robocze/comfyui/tla")
```

Czas na GTX 1060: ~60 s na obraz 1344×768 (6 kroków), pierwszy po starcie dłużej (ładowanie modelu).
