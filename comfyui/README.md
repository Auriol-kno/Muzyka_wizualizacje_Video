# ComfyUI – praca lokalna

ComfyUI generuje u nas **te same wizualizacje co potok** (cząsteczki i sceny 3D sterowane dźwiękiem) przez
węzły „Muzyka Graficznie”, a SDXL może je potem stylizować (img2img) albo dać tło.
Wszystko działa na tym komputerze (GTX 1060 6 GB), serwer słucha tylko na `127.0.0.1`.

## Węzły „Muzyka Graficznie” (`comfyui/wezly/`)

| Węzeł | Wejście | Wyjście |
|---|---|---|
| **klatki z dźwięku** (`MGKlatki`) | WAV, preset, chwile w s (`62, 211`), rozmiar, seed, podpis | `IMAGE` – klatki do podglądu lub img2img |
| **klip MP4** (`MGKlip`) | WAV, preset, od–do (0 = do końca), fps (też ułamek, np. 12,5), rozmiar, seed, podpis | ścieżka MP4, raport kontroli (JSON), 4 klatki podglądu |
| **kontrola jakości MP4** (`MGKontrola`) | pliki z „Video Combine” albo ścieżka MP4 | raport (JSON), ok – ta sama kontrola co w potoku (`skrypty/kontrola.py`) |

- Presety: sceny 3D `1_wyspa_poziomic` … `5_membrana_bessela` (z orbitą kamery, `3_gory_ze_strun` domyślny)
  i cząsteczkowe `1_cymatyka_zloty_piasek` … `5b_topografia_tory`.
- WAV: pełna ścieżka albo sama nazwa pliku z folderu `[udzial] zrodla`.
- Węzły nie liczą obrazu w Pythonie ComfyUI – wołają `skrypty/klatki.py` / `skrypty/animacja.py`
  Pythonem projektu. Wynik jest więc identyczny z potokiem: ruch z pomiaru nagrania, te same ścieżki kamery,
  −15 LUFS / −1,5 dBTP, H.264 + AAC 48 kHz, kontrola jakości w `.qc.json`. MP4 trafia do folderu `wyniki`.
- `MGKlip` blokuje kolejkę ComfyUI na czas renderu (postęp na pasku węzła i w konsoli). Cały Nokturn
  `3_gory_ze_strun` 720p25 to ~4 h – długie klipy lepiej puszczać z `skrypty/animacja.py`.

Gotowe workflowy (`comfyui/workflows/`, otwórz przeciągając plik na okno ComfyUI):

| Plik | Co robi | Czas na GTX 1060 |
|---|---|---|
| `wizualizacja_podglad.json` | klatki z 62 s i 211 s | ~25 s |
| `wizualizacja_stylizowana.json` | klatka 211 s → SDXL img2img (siła 0,35: kształt z dźwięku zostaje) | ~2 min |
| `wizualizacja_klip.json` | 10 s klipu 720p25 z podpisem + podgląd | ~1 min/2 s klipu |
| `wizualizacja_plynna.json` | render w 12,5 fps + RIFE ×2 → 25 fps (krótkie klipy) + kontrola | 5 s klipu: 185 s (bez RIFE 290 s) |
| `wizualizacja_ostrzejsza.json` | klip 720p → Real-ESRGAN ×2 → 1080p, partiami (także cały utwór) + kontrola | ~3 s/klatkę (5 s klipu: ~7 min; cały utwór ~5 h) |
| `tlo_sdxl.json`, `stylizacja_sdxl.json` | samo SDXL: tło / stylizacja wgranego obrazu | ~1 min |

## Dodatki (custom nodes) i modele

| Dodatek | Po co | Licencja |
|---|---|---|
| ComfyUI-Manager (wbudowany, `--enable-manager`) | instalacja / aktualizacja dodatków z interfejsu | GPL-3.0 |
| [ComfyUI-VideoHelperSuite](https://github.com/Kosinkadink/ComfyUI-VideoHelperSuite) | MP4 ↔ klatki, zapis H.264 z dźwiękiem, partie | GPL-3.0 |
| [ComfyUI-Frame-Interpolation](https://github.com/Fannovel16/ComfyUI-Frame-Interpolation) | RIFE: klatki pośrednie (model pobiera się przy pierwszym użyciu) | MIT |
| [ComfyUI-Crystools](https://github.com/crystian/ComfyUI-Crystools) | pasek zajętości karty / VRAM / RAM w interfejsie | MIT |
| `RealESRGAN_x2plus.pth`, `RealESRGAN_x4plus.pth` (`models/upscale_models`) | powiększanie | BSD-3 |

Instalacja (w `ComfyUI/custom_nodes`: `git clone --depth 1 <repo>`), zależności **z przypiętym PyTorch**, żeby
pip nie podmienił wersji cu126 na kompilację bez GTX 1060:
```powershell
<comfyui_folder>\python_embeded\python.exe -s -m pip install -c stale.txt -r ComfyUI\manager_requirements.txt opencv-contrib-python imageio-ffmpeg einops kornia scipy tqdm deepdiff pynvml py-cpuinfo piexif
```
`stale.txt`: `torch==2.14.1+cu126`, `torchvision==0.29.1+cu126`, `torchaudio==2.11.0+cu126`, `numpy==2.2.0`.
Bez CuPy (`install.py` Frame-Interpolation go instaluje) – RIFE go nie potrzebuje.
Unikamy `4x-UltraSharp` i podobnych: licencja CC BY-NC (bez użycia komercyjnego).

## Dwie instalacje – do czego która

| | ComfyUI portable | Comfy Desktop |
|---|---|---|
| Rola | serwer potoku i węzłów „Muzyka Graficznie” | ręczna praca, własne modele (LTX) |
| Adres | `http://127.0.0.1:8188` | `http://127.0.0.1:8189` (okno aplikacji) |
| Modele | `ComfyUI/models` + modele Desktop (przez `extra_model_paths.yaml`) | `Comfy-Desktop/ComfyUI-Shared/models` |

Obie dzielą jedną kartę 6 GB: przy dłuższym generowaniu zamknij tę drugą.

## Konfiguracja (raz)

1. `config/sciezki.toml` → `[narzedzia]`:
   ```toml
   comfyui_url = "http://127.0.0.1:8188"
   comfyui_folder = "D:/AI/ComfyUI_windows_portable_nvidia/ComfyUI_windows_portable"
   python = "C:/Users/<uzytkownik>/AppData/Local/Programs/Python/Python312/python.exe"   # Python projektu
   ```
2. Węzły: łącze katalogu z repo do ComfyUI (zmiany w repo działają od razu po restarcie serwera):
   ```powershell
   New-Item -ItemType Junction -Path "<comfyui_folder>\ComfyUI\custom_nodes\muzyka_graficznie" -Target "<repo>\comfyui\wezly"
   ```
3. Modele z Comfy Desktop widoczne w portable: `comfyui/extra_model_paths.example.yaml` →
   `ComfyUI/extra_model_paths.yaml` w folderze portable, popraw `base_path`. Zapisz **bez BOM** (UTF-8).
4. Modele SDXL w `ComfyUI/models/checkpoints` (obecnie `juggernautXL_v9Rdphoto2Lightning`).
   Licencję modelu sprawdzamy przed użyciem obrazu w klipie na YouTube.

### Aktualizacja ComfyUI a GTX 1060 (Pascal, sm_61)

`update_comfyui*.bat` aktualizuje kod i pakiety, ale **nie PyTorch**. ComfyUI ≥ 0.4x wymaga nowszego PyTorch
(`comfy_kitchen`). Do GTX 1060 bierzemy wersję **cu126** – kompilacje cu128/cu130 nie mają już kart Pascal:
```powershell
<comfyui_folder>\python_embeded\python.exe -m pip install --upgrade torch torchvision torchaudio --index-url https://download.pytorch.org/whl/cu126
```
Sprawdzenie: `torch.cuda.get_arch_list()` musi zawierać `sm_61`.

## Na co dzień

```powershell
python -m comfyui.uruchom          # stan; jeśli serwer nie działa – uruchom w tle i poczekaj (~30 s)
python -m comfyui.uruchom --stan   # tylko stan: wersja, karta, VRAM, checkpointy
python -m comfyui.uruchom --stop   # zatrzymaj serwer uruchomiony tym skryptem
python -m comfyui.workflowy        # zapisz workflowy do comfyui/workflows/*.json
```

Interfejs: http://127.0.0.1:8188 w przeglądarce. Dziennik serwera: `<robocze>/comfyui/serwer.log`.

## Zadania jednym poleceniem i kopie klipów

```powershell
python -m comfyui.zadanie plynna --od 205 --do 215     # podglad | klip | plynna | ostrzejsza
python -m comfyui.zadanie ostrzejsza --mp4 "D:/.../klip.mp4"
```
Czeka na koniec (z partiami VHS), wypisuje tylko krótkie podsumowanie z kontrolą jakości. Gotowy klip
trafia też do `<wyniki>/klipy/RRRR-MM-DD_GG-MM_<nazwa>.mp4` (data i godzina utworzenia na komputerze).
Jeśli w `config/sciezki.toml` → `[udzial]` jest `dysk_google = "<folder synchronizowany Dyskiem Google>"`,
kopia idzie także tam (Dysk Google na komputer wysyła ją sam).

## Panel „przepływ pracy” w przeglądarce

**http://127.0.0.1:8188/mg/panel** – strona wystawiana przez węzły „Muzyka Graficznie”
(`comfyui/wezly/panel.html`): bloki bieżącego workflow (○ czeka, ▶ liczy z paskiem postępu i czasem do
końca, ✓ gotowe, ✗ błąd), karta, VRAM, RAM, kolejka i historia; odświeżanie co 1,5 s. Działa w każdej
przeglądarce i w panelu przeglądarki aplikacji Claude.

## Panel „przepływ pracy” w aplikacji Claude (`comfyui/panel/`)

Mod Claude Code: panel obok rozmowy z blokami bieżącego workflow (○ czeka, ▶ liczy + pasek postępu,
✓ gotowe, ✗ błąd), VRAM, kolejką i historią zadań. Dane z `GET /mg/stan` – endpointu dodanego przez
węzły „Muzyka Graficznie” (zapis zdarzeń wykonania ComfyUI). Komenda `/przeplyw` otwiera panel.
Instalacja na stałe: folder `comfyui/panel` jako plugin (`claude --plugin-dir comfyui/panel`).

## Z Pythona

```python
from comfyui.klient import Comfy
from comfyui import workflowy as w
c = Comfy()
c.generuj(w.wizualizacja_podglad(czasy="30, 120"), "robocze/comfyui/klatki")
c.generuj(w.wizualizacja_stylizowana("golden threads, oil painting", czasy="211", sila=0.3), "robocze/comfyui/hybryda")
```
