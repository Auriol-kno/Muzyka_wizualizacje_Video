# Współpraca: właściciel + Claude + ChatGPT

## Jak się dogadujemy
Asystenci nie rozmawiają ze sobą bezpośrednio, tylko przez repo:
1. **`AGENTS.md`** – wspólne zasady (obaj czytają je na starcie).
2. **`docs/ZADANIA.md`** – kto co robi teraz (przed startem dopisz się, po skończeniu oznacz ✅).
3. **`docs/DZIENNIK.md`** – co zostało zrobione i jakie decyzje zapadły.
4. **Pull requesty** – każda zmiana idzie przez PR; drugi asystent może zrobić przegląd, właściciel scala.

Przekazując zadanie drugiemu asystentowi, właściciel wkleja mu link do PR / zadania – resztę kontekstu
znajdzie w repo.

## Proponowany podział (do potwierdzenia przez właściciela)
| Obszar | Główny | Wsparcie |
|---|---|---|
| Transkrypcja nut (PDF/nagranie → MIDI) | Claude | ChatGPT: przegląd nut |
| Brzmienie fortepianu, miks, głośność | Claude | |
| Animacja 2.5D w Pythonie (`utwory/*/render.py`) | Claude | |
| Sceny 3D w Blenderze (`blender/`) | do ustalenia | |
| Tła i tekstury z ComfyUI (`comfyui/`) | do ustalenia | |
| Opisy na YouTube, tytuły, miniatury | ChatGPT | Claude: fakty muzyczne |
| Kontrola jakości przed publikacją | Claude | właściciel ogląda |

## Gałęzie
`main` (zawsze działa) ← `claude/...`, `chatgpt/...`, `wlasciciel/...`
