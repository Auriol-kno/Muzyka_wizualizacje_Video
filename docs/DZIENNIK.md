# Dziennik projektu

## 2026-11-22 · Claude (7)
- Właściciel wybrał koncepcję 3 „Góry ze strun”: klip na tym samym nagraniu, **720p, 25 fps** (wyjątek od
  standardu 1080p30 na wyraźną prośbę właściciela), delikatny ruch kamery wokół.
- Przestrzeń wokół gór: ląd z nici do horyzontu, pierścień dalekich pasm, kopuła gwiazd (paralaksa),
  księżyc w kierunku kontry, mgła do 10 j. (gęstość liczona raz, dryfuje). Kamera: jedno okrążenie
  przez cały utwór, łagodny start i koniec, „oddech” odległości i wysokości (`kamera_struny`).
- `animacja.py`: sceny z `koncepcje_v2` (ścieżki kamery `SCIEZKI_KAMERY`), `--fps`, `--rozmiar`
  (render 1080p, skalowanie lanczos). Test 10 s (205–215 s): kontrola OK (10,0/10,0 s, brak czarnych
  klatek, skok jasności 0,53, −15,0 LUFS, −1,5 dBTP).

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
