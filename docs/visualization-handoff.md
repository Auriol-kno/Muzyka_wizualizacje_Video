# Przekazanie: muzyka i matematyka

## Cel
Pięć wizualizacji cząsteczkowych Nokturnu Es-dur op. 9 nr 2 Chopina, po dwie klatki (początek i środek), każda 1920 × 1080. Piasek, fale, rezonans, fraktale, kolor. Pełne wymagania i prompt: [claude-prompt.txt](claude-prompt.txt).

## Stan na 22 listopada 2026
- Repozytorium: https://github.com/Auriol-kno/Muzyka_wizualizacje_Video
- Zbadana baza: `main`, `4d1b0f052dc5e91c84ad35fe58c53c3de7d9636b`.
- Baza zawiera wyłącznie README. Nie ma aplikacji, zależności, audio ani gotowych klatek.
- W rozmowie wygenerowano koncepcyjne obrazy; nie zapisano ich do repozytorium. Nie są analizą nagrania ani kompletem eksportów Full HD.
- To przekazanie dokumentuje zakres; nie implementuje renderera.

## Podział pracy
- Codex: weryfikacja dostępu, przygotowanie briefu, przekazanie projektu. Gałąź: `codex/visualization-handoff`.
- Claude: następny krok — przeczytać prompt, sprawdzić aktualny stan repozytorium, wybrać stos dla nowego renderera i przygotować pięć presetów oraz eksport 10 osobnych klatek. Pracować na własnej gałęzi, np. `claude/visualization-renderer`.
- Nie zakładać, że Claude rozpoczął pracę lub przeczytał te pliki. Nie ma połączonych sesji ani automatycznego kanału komunikacji.

## Brakujące dane
Nie wskazano nagrania Nokturnu ani wykonawcy. Można opracować renderer i jawny tryb demonstracyjny. Dokładne czasy i synchronizacja wymagają wybranego pliku audio. Środek nagrania nie musi być kulminacją.

## Ustalenia graficzne
1. Złoty piasek: wzory inspirowane cymatyką.
2. Ocean harmonicznych: turkusowe i perłowe fale cząstek.
3. Fraktalny ogród: samopodobne rozgałęzienia.
4. Orbity rezonansu: przestrzenne krzywe Lissajous.
5. Topografia dźwięku: piaskowe wydmy i wieloskalowe kontury.

## Dostęp i diagnoza
Po aktualizacji uprawnień repozytorium pojawiło się na liście instalacji GitHub nr 176891368. Rzeczywiste utworzenie zdalnej gałęzi `codex/visualization-handoff` powiodło się. Początkowy błąd 403 dotyczył integracji, mimo zgłaszanego `push: true`; nie wystarczała deklaracja uprawnień użytkownika. Przekazanie znajduje się na osobnej gałęzi do przeglądu, bez scalania z main.

`git ls-remote` oraz `git clone` zadziałały poza sandboxem. W sandboxie most proxy był niedostępny. Wcześniejsze generacje obrazów ukończono, lecz limit prezentacji wyniku narzędzia pominął dwa obrazy; nie ma dowodu na awarię repozytorium. Są to odrębne zaobserwowane problemy.

## Sposób współpracy
Przed zmianami przeczytaj tę notatkę, sprawdź `git status`, pobierz aktualne zdalne referencje i zapisz używany commit. Zachowuj cudze zmiany. Używaj osobnych gałęzi. Po pracy dopisz w swoim PR: wykonane zadanie, zmienione pliki, komendy weryfikacyjne, wyniki, blokady i następny krok. Po uzgodnieniu zmian aktualizuj wspólną notatkę. Nie nadpisuj historii i nie scalaj cudzych zmian automatycznie. Komunikacja wymaga, aby sesja drugiego asystenta odczytała repozytorium lub PR; nie deklaruj dostarczenia wiadomości bez potwierdzenia.

## Sprawdzenie tego przekazania
Tylko dokumentacja; brak aplikacji do uruchomienia. Sprawdzono zawartość bazowego repozytorium, stan roboczy i zgodność lokalnego HEAD ze zdalnym. Przy wdrożeniu renderera trzeba sprawdzić 10 plików PNG, ich rozmiary, seed, stabilność kamery i reakcję na audio.
