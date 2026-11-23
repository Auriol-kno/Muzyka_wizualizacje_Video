# „Piasek fraktalny” – klip z dźwięku (2026-11-23)

Zlecenie właściciela: klip inspirowany grafiką piaskowych fal i fraktalnych wirów, na pełnym audio z pliku
`ostrzejsza_00002-audio.mp4`, wyrenderowany w ComfyUI, sprawdzony i wysłany na Dysk Google (folder TEMP).

## Źródło dźwięku
- Plik: `ComfyUI/output/muzyka_graficznie/ostrzejsza_00002-audio.mp4`, ścieżka AAC 48 kHz stereo, 4,992 s,
  −15,1 LUFS, szczyt −1,4 dBTP.
- Pochodzenie: wycinek 205–210 s z naszego klipu Nokturnu Es-dur op. 9 nr 2 (Chopin), nagranie Marthy
  Goldstein, **CC BY-SA 2.0** (`docs/ZRODLA.md`), więc klip jest na CC BY-SA, z atrybucją w opisie.
- W klipie: **niezmieniony strumień AAC źródła** (kopia, bez normalizacji, tempa i wysokości).

## Metoda
Proceduralny render w Pythonie wywoływany przez węzeł ComfyUI `MGPiasek`
(`comfyui/workflows/piasek_fraktalny.json`, `python -m comfyui.zadanie piasek --zrodlo <plik>`):
`skrypty/piasek.py` → `wizualizacje/piasek.py`. Render 1920×1080 (nadpróbkowanie 1,5×) →
INTER_AREA → 1280×720, 25 fps stałe, H.264 CRF 18, yuv420p, faststart. Klatki PNG zapisywane pojedynczo
(`<robocze>/piasek/<nazwa>/klatki`) – przerwany render wznawia się od brakujących.

Etap generatywny (SDXL img2img) sprawdzony osobno – patrz „Etap generatywny” niżej (odrzucony).

## Ustawienia
| | |
|---|---|
| seed świata | 20261123 (ziarna, wiry, zawirowania domeny) |
| kamera | stała, nisko nad powierzchnią; dryf 0,035 j./s (ledwie widoczny) |
| światło | kierunkowe z lewej-tyłu, elewacja ~16° (smuga po grzbietach) |
| głębia ostrości | płaszczyzna ostrości na ~74% wysokości kadru, rozmycie dal/blisko 1,2–2,6 px |
| paleta | tło granat-czerń; ziarna: szampańskie złoto, miedź, różowe złoto |

## Mapowanie dźwięk → obraz
Pomiar `wizualizacje/analiza.py` (obwiednie: atak 30 ms, zanik 0,6 s), dodatkowe wygładzenie geometrii
(EMA 0,12–0,25 s); fazy ruchu = całki z energii pasm, więc ruch zwalnia w ciszy i nigdy nie skacze.

| Dźwięk | Obraz |
|---|---|
| niskie 30–250 Hz | amplituda i przesuw szerokich wydm, głębokość lejów wirów; **pomarańczowa** barwa świateł i grzbietów wydm |
| średnie 250–2000 Hz | siła i obrót spiralnych grzbietów, interferencje pierścieni |
| wysokie 2–8 kHz | drobne zmarszczki, iskrzenie i unoszenie ziaren; **niebieska** barwa świateł i iskier |
| ataki (8 w nagraniu) | pierścień-impuls od jednego z trzech widocznych wirów, zanik 0,65 s |
| wybrzmienie | obwiednie opadają powoli → łagodniejsze fale |
| złożoność = 0,55·średnie + 0,45·bogactwo brzmienia (liczba klas wysokości) | udział 2. i 3. poziomu fraktala wirów (nie zależy od czasu) |

Przebieg nagrania: 0–1,4 s spokojnie; 1,5–2,0 s szczyt średnich (silniejsze wiry); 2,2–2,8 s szczyt basu
(wyższe wydmy, pomarańcz); 3,0–3,8 s cicho; 4,0 s szczyt wysokich (błękitne iskry i zmarszczki).

## Modele i węzły
- Węzeł `MGPiasek` (nasz, `comfyui/wezly`), `PreviewImage`. Modele AI w klipie: brak (patrz niżej).
- Środowisko: ComfyUI 0.46.0 portable, PyTorch 2.14.1+cu126, GTX 1060 6 GB; Python 3.12 (numpy, OpenCV).

## Etap generatywny – test i decyzja
SDXL img2img (`juggernautXL_v9Rdphoto2Lightning`, siła 0,3, 6 kroków, seed 7, ten sam prompt) na klatkach
60 i 61: piasek z ziaren zamienia się w gładką „wiklinę”, a wzór detalu zmienia się między klatkami –
średnia różnica sąsiednich klatek rośnie z 3,08 do 4,82 (migotanie), ~60 s/klatkę na GTX 1060.
Decyzja: klip bez etapu generatywnego (czysty render proceduralny zachowuje ziarno, ciągłość i reakcję na
dźwięk).

## Wynik i kontrola
- `wyniki/klipy/2026-11-23_11-07_piasek_fraktalny_1280x720_25fps.mp4` (+ `.qc.json`, `.workflow.json`);
  na Dysku Google w folderze TEMP. Render 125 klatek w 460 s (6 procesów).
- ffprobe: H.264 High, yuv420p, 1280×720, 25/1 fps (avg 25/1), 125 klatek, 5,000 s; AAC LC 48 kHz stereo
  4,992 s – MD5 strumienia identyczny ze źródłem; moov przed mdat (faststart).
- Kontrola: brak czarnych klatek, brak zatrzymań (freezedetect), dekodowanie bez błędów, największy skok
  średniej jasności 2,85/255 (płynne narastanie przy ataku basu), −15,1 LUFS, −1,4 dBTP.
- Obejrzane: początek (spokój), środek (szczyt basu – pomarańcz), koniec (wysokie – błękit), kolejne
  klatki wokół ataku 1,56 s i pierścień po ataku 2,21 s. Render jednym przebiegiem – bez łączeń segmentów.
