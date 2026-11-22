# Potok produkcji klipu

```
nuty (PDF) ──► transkrypcja ─┐
nagranie ────► analiza widma ┴► MIDI ──► synteza fortepianu ──► WAV (−15 LUFS)
                                  │                                 │
                                  └──► render obrazu (Python) ──► MP4 ◄┘ ──► kontrola jakości
                                        (później: Blender / ComfyUI)
```

1. **MIDI** – jedno źródło prawdy. Kanał 0 = melodia, kanał 1 = pozostałe głosy. Markery = części utworu.
   - z nut: `utwory/<utwór>/<budowa>.py` (zapis nut w kodzie), pomoc: `bach_goldberg_aria/omr.py`
     (odczyt wysokości główek nut z obrazu);
   - z nagrania: `vivaldi_jesien_allegro/transcribe.py` (melodia z widma + Viterbi, tempo, akordy z chromy).
2. **Dźwięk** – `wspolne/piano_synth.py` (fortepian) lub `wspolne/piano_soft.py` (łagodne pianino),
   potem normalizacja ffmpeg `loudnorm=I=-15:TP=-1.5`.
3. **Obraz** – `utwory/<utwór>/render.py`: wszystko jest funkcją czasu i nut z MIDI, klatki liczone
   równolegle, kodowanie H.264 w segmentach.
4. **Złożenie i kontrola** – `skrypty/zbuduj.py`: łączy segmenty z dźwiękiem, sprawdza długości.

Zmienne środowiskowe renderu: `RES` (1 = 1080p, 2 = 4K), `DUR` (s), `MIDI`, `PROCS`.
