# Dziennik projektu

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
