# Przekazanie: wizualizacje cząsteczkowe (Claude ↔ Codex)

## Cel
Wizualizacje związków muzyki i matematyki (fale, rezonans, interferencja, piasek, fraktale) sterowane
**pomiarem audio**. Pierwszy rezultat: Chopin – Nokturn Es-dur op. 9 nr 2, 5 kierunków × 2 klatki
(początek pierwszej frazy i połowa tego samego wykonania), PNG 1920×1080 + manifest.

## Stan (2026-11-22, Claude, gałąź `claude/nokturn-wizualizacje`)
- ✅ `wizualizacje/analiza.py` – pomiar: RMS + obwiednia (szybki atak / wolny zanik), STFT, energia pasm
  (30–250 / 250–2000 / 2000–8000 Hz), centroid, ataki (strumień widmowy), szczyty widma, chroma.
- ✅ `wizualizacje/czasteczki.py` – renderer cząsteczkowy offline (numpy/OpenCV, kamera perspektywiczna,
  głębia ostrości, poświata, stały seed) i 5 presetów: cymatyka (inspiracja Chladnim, nie model fizyczny),
  ocean harmonicznych, fraktalny ogród, orbity rezonansu (Lissajous z ułamków p/q), topografia dźwięku.
  Każdy preset zwraca `parametry`, które trafiają do manifestu.
- ✅ `skrypty/nokturn_klatki.py` – `--audio plik` lub `--demo`; manifest JSON, arkusz porównawczy,
  kontrola wymiarów i reakcji na ciszę.
- ✅ Demo uruchomione i obejrzane (10 klatek 1920×1080, kontrola ciszy = zera). Topografia rozjaśniona
  i bez szwu na środku kadru. **Następny krok: właściciel ocenia kierunki** (`arkusz_porownawczy.png`
  w `robocze/nokturn_op9_2_klatki`).

## Blokady
- **Brak nagrania Nokturnu** o znanym źródle i licencji → dokładna synchronizacja zablokowana.
  Tryb demo używa własnej frazy testowej w Es-dur (nie Chopin) i oznacza klatki napisem „DEMO”.
- ~~Zapis na GitHub~~: rozwiązane 2026-11-22 – lokalne repo w `D:\AI\PROJEKT_MUZYCZNY\Muzyka_wizualizacje_Video`
  pushuje na GitHub przez Git Credential Manager (logowanie właściciela). Aplikacje Claude/Codex na
  GitHubie nadal mogą dostawać 403 – to osobna sprawa.

## Weryfikacja
```
python skrypty/nokturn_klatki.py --demo --out <folder>
python skrypty/nokturn_klatki.py --audio <nagranie.wav> --zrodlo "wykonawca, źródło, licencja"
```
Sprawdzić: 10 plików 1920×1080, para = ta sama kamera/seed/paleta, `manifest.json` (tryb, czasy,
parametry, `kontrola_ciszy` ≈ zera), obejrzeć `arkusz_porownawczy.png`.

## Przydział
| Zadanie | Kto |
|---|---|
| Analiza audio, renderer, 5 presetów, manifest | Claude |
| Wybór nagrania (źródło + licencja) | właściciel / Codex (propozycje) |
| Ocena kierunków wizualnych, wybór do animacji | właściciel |
