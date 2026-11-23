# Blender (w przygotowaniu)

Cel: sceny 3D wyższej jakości (prawdziwe odbicia, szkło, głębia ostrości) sterowane tym samym MIDI.

Plan:
1. Skrypt `blender/midi_do_klatek.py` – czyta MIDI (`wspolne/midi_io.py`) i tworzy klatki kluczowe
   (kule na torze, wciśnięte klawisze, emisja segmentów koła).
2. Scena bazowa `Muzyka_Graficznie_baza.blend` – leży na udziale (nie w repo), kamera 1920×1080 / 30 fps.
3. Render przez wiersz poleceń: `blender -b scena.blend -P blender/midi_do_klatek.py -- --midi ... --out ...`.

Do ustalenia z właścicielem: wersja Blendera, silnik (Eevee szybciej, Cycles ładniej), karta graficzna.
