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

## Wersja 2 – piasek 3D (uwagi właściciela, 2026-11-23)
Uwagi: większa, widoczna amplituda; wysokie tony = najwyższa dodatnia amplituda, basy = ujemna; kolory
odwrotnie (niskie → niebieski, wysokie → pomarańcz); gra światła, mienienie się ziaren; „nic się nie
rusza” – animacja ma być głęboka i dynamiczna, każdy dźwięk widoczny na cząsteczkach.

`wizualizacje/piasek3d.py` (domyślne w `skrypty/piasek.py`, `--wersja 3d`): ~4,4 mln ziaren na siatce
14 × 13 j. (gęściej przy kamerze), bufor głębokości (bliższe ziarna zasłaniają dalsze), głębia ostrości.
Kamera nisko nad piaskiem (2,55 j.), powolny najazd 5,6 → 4,8 j. i obrót −7° → +5° (łagodny start/stop).

| Dźwięk | Obraz |
|---|---|
| wysokie 2–8 kHz | wzgórza i szczyty rosną w górę (do ~0,75 j.); barwa **pomarańczowa** (wg dodatniej wysokości) |
| niskie / bas | doliny i leje wirów zapadają się (do ~−0,9 j.); barwa **niebieska** (wg ujemnej wysokości) |
| każdy półton C2–B6 (widmo) | własne miejsce na piasku (wysokość dźwięku → w poprzek, krąg kwintowy → w głąb); powyżej E4 wybrzuszenie w górę, poniżej w dół, z koncentryczną zmarszczką; obwiednia atak 30 ms / zanik 0,45 s |
| średnie | obrót i wysokość spiralnych grzbietów 5 wirów |
| ataki | pierścień-fala (do 0,22 j.) od jednego z trzech wirów |
| mienienie | każde ziarno ma mikrościankę obracaną z prędkością 0,4–2 rad/s × (0,6 + 2,2·wysokie + 1,2·energia); błysk ∝ (n·h)^60 |

Wynik: `wyniki/klipy/2026-11-23_11-33_piasek_fraktalny_3d_1280x720_25fps.mp4` (wzorzec CRF 18, 10,1 MB,
render 290 s). Kontrola OK: 125 klatek, 5,000 s / audio 4,992 s (MD5 strumienia = źródło), brak czarnych
klatek i zatrzymań, faststart, największy skok jasności 1,01. Ruch: średnia różnica sąsiednich klatek 7,3
(wersja 1: 1–3,6); mienienie: ~8% pikseli na klatkę zmienia jasność o > 25/255.
Na Dysk Google (limit połączenia ~7,5 MB) poszła wersja dwuprzebiegowa 11 Mb/s z tych samych klatek
(6,8 MB, SSIM 0,972 względem wzorca), audio identyczne.

## Wersja 3 – amplituda +20% (prośba właściciela)
`AMPLITUDA = 1.2` w `wizualizacje/piasek3d.py` (cała wysokość piasku ×1,2). Wynik:
`wyniki/klipy/2026-11-23_12-03_piasek_fraktalny_3d_amp120_1280x720_25fps.mp4` (CRF 18, 10,4 MB); na Dysku
wersja 11 Mb/s (6,8 MB). Kontrola OK (125 klatek, 5,000 s, audio = źródło, skok jasności 0,96, brak
zatrzymań). Render wznowiony po przerwaniu (6 procesów × ~2,5 GB RAM przekroczyło pamięć) – klatki 0–95
i 96–124 z dwóch przebiegów, łączenie niewidoczne (różnica sąsiednich klatek 11,6 → 12,2, zgodnie z
narastaniem przed atakiem 3,95 s). Domyślnie 4 procesy.

## Wersja długa – cały Nokturn (prośba właściciela)
Ten sam renderer (wersja 3, amplituda ×1,2), źródło dźwięku: nasz klip „Góry ze strun” (cały Nokturn,
nagranie M. Goldstein, CC BY-SA 2.0, −15,2 LUFS) – strumień AAC skopiowany bez zmian.
`python -m comfyui.zadanie piasek --zrodlo <góry ze strun>.mp4 --nazwa nokturn_piasek_fraktalny_3d_1280x720_25fps`

- Wynik: `wyniki/klipy/2026-11-23_17-54_nokturn_piasek_fraktalny_3d_1280x720_25fps.mp4` (549 MB, CRF 18)
  + `.qc.json`. Na Dysku Google (limit połączenia ~7,5 MB) tylko fragment 200–212 s (2 przebiegi 4,3 Mb/s).
- Render 6328 klatek: 4 h 15 min + 1 h 6 min (≈3 s/klatkę, 4 procesy). Pierwszy przebieg przerwał się na
  klatce 5038 (`PermissionError` przy uruchamianiu procesów potomnych – prawdopodobnie narastanie pamięci);
  od tej pory pula wymienia procesy co 250 klatek (`maxtasksperchild=250`).
- Kontrola OK: H.264 High yuv420p 1280×720, 25/1 fps, 6328 klatek, 253,12 s = audio 253,12 s, MD5
  strumienia audio identyczny ze źródłem, moov przed mdat, brak czarnych klatek, freezedetect (2 s) – brak
  zatrzymań, największy skok jasności 1,4, −15,2 LUFS / −1,4 dBTP.
- Łączenie przebiegów (klatka 5037 → 5038): różnica sąsiednich klatek 9,4 przy 8,0–9,6 w otoczeniu –
  niewidoczne. Obejrzane klatki 0, 1500, 3164, 5037, 5038, 6327.
