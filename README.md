# Muzyka Graficznie – wizualizacje muzyki klasycznej z matematyką

Klipy na YouTube dla dzieci i dorosłych: muzyka klasyczna na fortepianie i animacja, w której każdy ruch
wynika z nut. Kule toczą się po torze do klawiatury, koło kwintowe pokazuje harmonię, a po bokach rosną
fraktale i spirale powiązane z melodią.

## Gotowe utwory

| Utwór | Folder | Matematyka po bokach | Długość |
|---|---|---|---|
| Chopin – Walc a-moll B.150 | `utwory/chopin_walc_a-moll` | trójkąt Pascala → Sierpiński, ciąg Fibonacciego → złota spirala | 1:49 |
| Bach – Wariacje Goldbergowskie, Aria | `utwory/bach_goldberg_aria` | fyllotaksja (kąt złoty), krzywe pościgu → spirale logarytmiczne | 3:15 |
| Vivaldi – Jesień, Allegro | `utwory/vivaldi_jesien_allegro` | drzewo fraktalne (liście = nuty), spirala częstotliwości | 5:08 |

## Szybki start (Windows)

```powershell
# 1. Python 3.11+ i ffmpeg (np. winget install Gyan.FFmpeg) w PATH
python -m venv .venv
.venv\Scripts\activate
pip install -r requirements.txt

# 2. Ścieżki do udziału z mediami
copy config\sciezki.example.toml config\sciezki.toml   # i popraw ścieżki

# 3. Budowa
python skrypty\zbuduj.py vivaldi_jesien_allegro --test 30 90   # klatki testowe PNG
python skrypty\zbuduj.py vivaldi_jesien_allegro                # pełny klip 1080p na udział
```

Render 1080p trwa ok. 0,3–0,5 s na klatkę na rdzeń (5-minutowy utwór: kilkanaście–kilkadziesiąt minut,
zależnie od liczby rdzeni; zmienna `PROCS` ustawia liczbę procesów).

## Jak to działa
Opis potoku: [`docs/PIPELINE.md`](docs/PIPELINE.md). Styl serii: [`docs/STYL_SERII.md`](docs/STYL_SERII.md).
Zasady współpracy ludzi i asystentów AI: [`AGENTS.md`](AGENTS.md) i [`docs/WSPOLPRACA.md`](docs/WSPOLPRACA.md).
