# Dziennik projektu

## 2026-11-23 · Claude (10)
- Dodatki ComfyUI (prośba właściciela, pakiet 1): Manager (wbudowany, `--enable-manager` w `uruchom.py`),
  VideoHelperSuite, Frame-Interpolation (RIFE), Crystools; modele Real-ESRGAN ×2/×4 (BSD-3; 4x-UltraSharp
  odrzucony – CC BY-NC). Zależności instalowane z przypiętym PyTorch 2.14.1+cu126, bez CuPy; `pip check` OK.
- Nowy węzeł `MGKontrola` (kontrola jakości jak w potoku, `skrypty/kontrola.py`) i ułamkowe fps w
  `animacja.py`/`MGKlip` (12,5 fps pod RIFE). Workflowy: `wizualizacja_plynna` (12,5 fps + RIFE ×2 → 25 fps:
  5 s klipu w 185 s zamiast 290 s; kontrola OK: 4,92/4,91 s, skok 0,54, −15,1 LUFS, −1,4 dBTP) i
  `wizualizacja_ostrzejsza` (720p → Real-ESRGAN ×2 → 1080p partiami po 32 klatki, ~3 s/klatkę; kontrola OK:
  5,0/4,99 s, skok 0,51, −15,1 LUFS, −1,4 dBTP).
- `python -m comfyui.zadanie`: workflow → kolejka → czekanie → podsumowanie z kontrolą; kopia klipu do
  `<wyniki>/klipy/RRRR-MM-DD_GG-MM_<nazwa>.mp4` (+ opcjonalnie folder Dysku Google). Klipy wysyłane też na
  Dysk Google właściciela (folder TEMP). Test: płynna 10 s (205–215 s) w 343 s, kontrola OK (9,96/9,94 s,
  skok 0,55, −15,0 LUFS, −1,3 dBTP).
- Panel „przepływ pracy” (mod Claude, `comfyui/panel/`) + endpoint `GET /mg/stan` w węzłach: bloki
  workflow na żywo (czeka / liczy z postępem / gotowe / błąd), VRAM, kolejka, historia.

## 2026-11-23 · Claude (9)
- ComfyUI generuje nasze wizualizacje (prośba właściciela): węzły „Muzyka Graficznie” (`comfyui/wezly/`,
  łącze katalogu w `custom_nodes/muzyka_graficznie`): `MGKlatki` (klatki z dźwięku → IMAGE) i `MGKlip`
  (klip MP4 jak w potoku + kontrola jakości). Węzły wołają `skrypty/klatki.py` / `animacja.py` Pythonem
  projektu (`[narzedzia] python`), więc obraz jest identyczny z potokiem. Workflowy: podgląd, hybryda
  (klatka → SDXL img2img, siła 0,35), klip. Gałąź `claude/comfyui-hybryda` scalona do `claude/koncepcje-v2`.
- Właściciel zaktualizował ComfyUI portable 0.3.9 → 0.46 (`update_comfyui_stable.bat`); nowy kod wymaga
  nowszego PyTorch (`comfy_kitchen`). PyTorch 2.5.1+cu124 → **2.14.1+cu126** (cu128/cu130 nie wspierają
  GTX 1060 / sm_61). Sprawdzone: `sm_61` na liście, mnożenie macierzy na karcie OK.
- Testy przez API (0.46, nowy PyTorch): podgląd 2 klatek 26 s; hybryda 135 s; klip 5 s (205–210 s, 720p25)
  290 s – kontrola OK (5,0/5,0 s, brak czarnych klatek, skok jasności 0,52, −15,1 LUFS, −1,5 dBTP).

## 2026-11-23 · Claude (8)
- ComfyUI do pracy lokalnej (prośba właściciela): `python -m comfyui.uruchom` sprawdza/uruchamia serwer
  portable w tle (tylko 127.0.0.1:8188, folder z `comfyui_folder` w `config/sciezki.toml`, dziennik w
  `<robocze>/comfyui/serwer.log`), `--stan`, `--stop`. Portable widzi modele Comfy Desktop przez
  `extra_model_paths.yaml` (wzór w repo; bez BOM – inaczej 0.3.9 nie startuje). Workflowy jako JSON w
  `comfyui/workflows/` do otwarcia w interfejsie. Test: tło SDXL 1344×768 wygenerowane przez klienta (184 s
  z ładowaniem modelu). Desktop (8189) zostaje do ręcznej pracy; obie instalacje dzielą kartę 6 GB.
## 2026-11-22 · Claude (7)
- Właściciel wybrał koncepcję 3 „Góry ze strun”: klip na tym samym nagraniu, **720p, 25 fps** (wyjątek od
  standardu 1080p30 na wyraźną prośbę właściciela), delikatny ruch kamery wokół.
- Przestrzeń wokół gór: ląd z nici do horyzontu, pierścień dalekich pasm, kopuła gwiazd (paralaksa),
  księżyc w kierunku kontry, mgła do 10 j. (gęstość liczona raz, dryfuje). Kamera: jedno okrążenie
  przez cały utwór, łagodny start i koniec, „oddech” odległości i wysokości (`kamera_struny`).
- `animacja.py`: sceny z `koncepcje_v2` (ścieżki kamery `SCIEZKI_KAMERY`), `--fps`, `--rozmiar`
  (render 1080p, skalowanie lanczos). Test 10 s (205–215 s): kontrola OK (10,0/10,0 s, brak czarnych
  klatek, skok jasności 0,53, −15,0 LUFS, −1,5 dBTP).
- 2026-11-23: pełny klip (6328 klatek, 2,2 s/klatkę, 3 h 53 min): kontrola OK – obraz 253,12 s / dźwięk
  253,12 s, brak czarnych klatek, największy skok jasności 0,52, −15,2 LUFS, −1,4 dBTP, h264 1280×720
  25 fps + AAC 48 kHz, 79 MB. Plik w `wyniki/` (`…_3_gory_ze_strun_1280x720_25fps.mp4`).

## 2026-11-22 · Claude (6)
- Wersja 2, runda 2 (`inspiracje/2 wariacja`, prośba właściciela: dużo drobin, kamera wokół motywu, światło,
  rozbłyski, gradienty): `wizualizacje/koncepcje_v2.py` – sceny 3D z orbitą kamery (2–3 mln drobin):
  1 wyspa poziomic, 2 wstęga iskier (Möbius), 3 góry ze strun (nuta → struna drga), 4 dolina nokturnu,
  5 membrana Bessela (tryby J_m(kr)cos(mθ) z widma). Światło stałe w świecie (klucz + kontra), flara obiektywu,
  rozbłyski gwiazdkowe, smuga anamorficzna, mgła głębi, tonemapping „screen” + korekta. Złoto: nasycone odcienie
  (jasne bielały w tonemappingu). Podglądy + klipy orbity: `skrypty/koncepcje2_podglad.py`; przegląd w Claude Design.

## 2026-11-22 · Claude (5)
- Wersja 2 Nokturnu: pięć koncepcji łączących motywy z `zrodla/inspiracje/` (`wizualizacje/koncepcje.py`):
  A złote poziomice, B rzeka iskier, C złota spirala (φ), D kryształ w jedwabiu, E pejzaż nokturnu (połączenie).
  Wszystko sterowane pomiarem nagrania. Podglądy: `skrypty/koncepcje_podglad.py` → `robocze/koncepcje_v2/`
  (cicho 62 s / głośno 211 s + tablica `przeglad_koncepcji.jpg`). Klatka 1–4 s w jednym procesie.

## 2026-11-22 · Claude (4)
- ComfyUI 0.3.9 działa na GTX 1060 6 GB (SDXL Lightning ~60 s/obraz); klient API w `comfyui/`.
- Nagranie Nokturnu: Martha Goldstein (2006), CC BY-SA 2.0 – wpis w `docs/ZRODLA.md`;
  użycie jako dźwięku klipu czeka na decyzję właściciela.
- Właścicielowi spodobała się topografia → nowy wariant `5b_topografia_tory` w kolorach z
  `inspiracje/styl_tory_kulki.jpg` (kolor ← wysokość terenu i centroid, wiry po atakach różowe).
- `nokturn_klatki.py --podpis`: podpis utworu i wykonawcy w prawym dolnym rogu (prośba właściciela).
- `skrypty/animacja.py`: jedno polecenie WAV → MP4 (normalizacja −15 LUFS/−1,5 dBTP, 8 procesów,
  kodowanie H.264 w locie, kontrola jakości do `.qc.json`). Topografia przyspieszona (teren bazowy liczony
  raz, wiry tylko lokalnie): ~1 s/klatkę przy 8 procesach. Wiry narastają 0,1 s (bez szarpnięć).
  Test 10 s: kontrola OK (długości równe, brak czarnych klatek, skok jasności 0,45, −14,3 LUFS, −1,5 dBTP).
- Pełny Nokturn (`5b_topografia_tory`, 4:13, 7594 klatek, ~2 h 12 min przy 1,04 s/klatkę): kontrola OK –
  obraz 253,133 s / dźwięk 253,120 s, brak czarnych klatek, największy skok jasności 2,2, −15,2 LUFS,
  −1,4 dBTP, h264 1080p30 + AAC 48 kHz. Plik w `wyniki/` (498 MB).
- Decyzja właściciela: dźwięk klipu = nagranie Marthy Goldstein (CC BY-SA 2.0), klip na CC BY-SA.
  Wyjątek dopisany w `AGENTS.md`, decyzja w `docs/ZRODLA.md`, opis filmu z atrybucją w
  `docs/opisy/nokturn_op9_2.md`.

## 2026-11-22 · Claude (3)
- Na komputerze z Windows zainstalowane: Python 3.12, pakiety z `requirements.txt`, ffmpeg, Git.
  Repo postawione z `repo.bundle`, gałęzie `claude/*` wypchnięte na GitHub (zapis działa).
- Pierwsze demo klatek Nokturnu obejrzane: presety 1–4 w porządku. Topografia (5) była prawie
  niewidoczna (jasność p99 = 27) i miała pionowy szew na środku kadru (błąd okresu w `szum`:
  `mod(n−1)` + `mode="wrap"`). Poprawione: wzmocnienie świecenia, jaśniejsze stoki w cieniu,
  `mode="grid-wrap"`. Po poprawce p99 = 76–83, szwu brak.

## 2026-11-22 · Claude (2)
- Nowy kierunek: wizualizacje cząsteczkowe sterowane pomiarem audio (`wizualizacje/`), przekazanie od Codexa
  opisane w `docs/visualization-handoff.md`. Folder roboczy na Windows: `D:\AI\PROJEKT_MUZYCZNY`.

## 2026-11-22 · Claude
- Założona struktura repo: `wspolne/`, `utwory/`, `skrypty/zbuduj.py`, `docs/`, `blender/`, `comfyui/`.
- Przeniesione trzy gotowe potoki (Chopin, Bach, Vivaldi); ścieżki i fonty niezależne od systemu.
- Ustalone: media na udziale Windows, w repo tylko kod/MIDI/dokumentacja (`.gitignore`).

## 2026-11-20 · Claude
- Vivaldi v2: łagodniejsze pianino (mniej basu, jaśniejsza barwa, humanizacja, lżejszy akompaniament,
  −15 LUFS). Powód: uwaga właściciela, że dźwięk był „zbyt niski” i brzmiał sztucznie.

## 2026-11-12 · Claude
- Bach: Aria z Wariacji Goldbergowskich (transkrypcja z PDF, wysokości odczytane skryptem `omr.py`).
- Vivaldi: Jesień, Allegro – nuty odczytane z nagrania (analiza widma), aranżacja na fortepian.
- Chopin v2: prosta klawiatura z nazwami nut, większe koło kwintowe, fraktale Pascal/Fibonacci.

## 2026-11-11 · Claude
- Chopin: cały Walc a-moll B.150 z powtórzeniami (transkrypcja z nut), styl neonowy, koło kwintowe.
