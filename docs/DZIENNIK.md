# Dziennik projektu

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
