# Zasady dla asystentów AI (Claude, ChatGPT / Codex i inni)

Ten plik czytają wszyscy asystenci pracujący nad repo. Claude czyta go przez `CLAUDE.md`, ChatGPT/Codex bezpośrednio.
Jeśli zasady się zmieniają, zmieniamy je **tutaj**, w jednym miejscu.

## Projekt w jednym zdaniu
„Muzyka Graficznie” to seria klipów na YouTube dla dzieci i dorosłych: muzyka klasyczna grana na fortepianie
+ animacja, w której **każdy ruch wynika z nut (MIDI)**, a po bokach pokazujemy matematykę pasującą do utworu.

## Podział pracy
- **Właściciel projektu (człowiek)** decyduje o kierunku, akceptuje zmiany (merge do `main`), publikuje na YouTube.
- **Claude** – potoki w Pythonie (nuty → MIDI → dźwięk → render → MP4), transkrypcje, kontrola jakości.
- **ChatGPT** – zgodnie z ustaleniami w `docs/WSPOLPRACA.md` (np. scenariusze, opisy, Blender, ComfyUI).
- Kto zaczyna zadanie, wpisuje je w `docs/ZADANIA.md` (kto, co, gałąź), żeby dwa asystenty nie robiły tego samego.

## Git
- Nie commitujemy bezpośrednio do `main`. Każdy pracuje na własnej gałęzi:
  `claude/<krótki-opis>`, `chatgpt/<krótki-opis>`, potem pull request do `main`.
- Przed rozpoczęciem pracy: `git pull` na `main` i przeczytanie `docs/DZIENNIK.md` (ostatnie wpisy).
- Małe, opisowe commity po polsku, np. `vivaldi: łagodniejsze brzmienie fortepianu`.
- Po każdej istotnej zmianie dopisz krótki wpis do `docs/DZIENNIK.md` (data, kto, co, dlaczego).
- **Nie zmieniaj cudzej gałęzi** bez prośby właściciela. Konflikt? Opisz go w PR, nie nadpisuj.

## Pliki i ścieżki
- W repo trzymamy tylko kod, MIDI, konfiguracje, workflowy i dokumentację.
- **Media (MP4, WAV, PNG, .blend, modele) leżą na udziale sieciowym** na komputerze z Windows,
  ścieżki w `config/sciezki.toml` (lokalny, poza repo; wzór: `config/sciezki.example.toml`).
- Nigdy nie wpisuj na sztywno ścieżek typu `C:\Users\...` ani `/home/...` w kodzie – używaj konfiguracji
  albo ścieżek względnych do `ROOT` repo.
- Kod musi działać na Windows (ścieżki przez `pathlib`, bez poleceń bash w krokach budowania).

## Standard klipu (nie zmieniaj bez zgody właściciela)
- MP4, H.264 + AAC 48 kHz, 30 fps. Podgląd: 1920×1080 (domyślnie, oszczędnie). 4K tylko na wyraźną prośbę.
- Brzmienie: fortepian / łagodne pianino. Głośność: −15 LUFS, szczyt −1,5 dBTP.
- Bez znaków wodnych. Napisy edukacyjne tylko wtedy, gdy mają znaczenie muzyczne, krótkie, po polsku.
- Synchronizacja: obraz liczony z tego samego pliku MIDI co dźwięk.
- Przed oddaniem: kontrola długości (obraz = dźwięk), brak czarnych klatek, brak skoków jasności,
  głośność. Wyniki kontroli wpisz w PR.

## Struktura repo
- `wspolne/` – biblioteki: odczyt/zapis MIDI, synteza fortepianu, parser SoundFont.
- `utwory/<utwór>/` – wszystko dla jednego utworu: budowa MIDI, `render.py`, plik `.mid`.
- `skrypty/zbuduj.py` – jedno polecenie budujące cały klip.
- `blender/`, `comfyui/` – integracje (w budowie), opis w ich README.
- `docs/` – współpraca, potok, styl serii, dziennik, zadania.
- `assets/fonts/` – fonty używane w napisach.

## Prawa autorskie
- Używamy tylko utworów w domenie publicznej i własnych wykonań (synteza z MIDI).
- Nagrania cudzych wykonań służą najwyżej do odczytu nut; ich licencję i autora zapisujemy w
  `docs/ZRODLA.md` i podajemy w opisie filmu.
- Wyjątek: cudze nagranie może być ścieżką dźwiękową klipu **tylko po decyzji właściciela**, zapisanej
  w `docs/ZRODLA.md`, i tylko na wolnej licencji (np. CC BY / CC BY-SA). Wtedy w opisie filmu: autor,
  link do źródła i licencji, informacja o zmianach; przy CC BY-SA cały klip udostępniamy na CC BY-SA.
  Obecnie dotyczy: Chopin, Nokturn op. 9 nr 2 (Martha Goldstein, CC BY-SA 2.0). Wizualizacja liczona
  jest wtedy z pomiaru nagrania (`wizualizacje/analiza.py`), nie z MIDI.
