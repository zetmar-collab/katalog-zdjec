# Katalog Zdjęć

Aplikacja do automatycznego porządkowania i przeglądania zdjęć.
Sortuje fotografie do folderów **rok / tydzień** na podstawie danych EXIF,
obsługuje import z aparatu, telefonu, USB i kart SD.

---

## Spis treści

1. [Wymagania](#wymagania)
2. [Instalacja — Linux](#instalacja--linux)
3. [Instalacja — Windows](#instalacja--windows)
4. [Pierwsze uruchomienie](#pierwsze-uruchomienie)
5. [Obsługa aplikacji](#obsługa-aplikacji)
6. [Skróty klawiszowe](#skróty-klawiszowe)
7. [Odinstalowanie](#odinstalowanie)

---

## Wymagania

| System   | Minimalna wersja       |
|----------|------------------------|
| Python   | 3.8 lub nowszy         |
| PyQt5    | 5.15 lub nowszy        |
| Pillow   | 10.0 lub nowszy        |
| exifread | 3.0 lub nowszy         |

---

## Instalacja — Linux

### Metoda automatyczna (zalecana)

1. Otwórz terminal w folderze z aplikacją.
2. Nadaj uprawnienia i uruchom instalator:

```bash
chmod +x install_linux.sh
bash install_linux.sh
```

Instalator automatycznie:
- sprawdzi wersję Pythona,
- zainstaluje brakujące pakiety (apt/pip),
- skopiuje pliki do `~/.local/share/katalog-zdjec/`,
- doda skrót do menu aplikacji oraz polecenie `katalog-zdjec` w terminalu.

### Metoda ręczna

```bash
# 1. Zainstaluj zależności systemowe
sudo apt update
sudo apt install python3 python3-pip python3-pyqt5 python3-pil

# 2. Zainstaluj pakiety pip
pip3 install --user -r requirements.txt

# 3. Uruchom aplikację
python3 main.py
```

---

## Instalacja — Windows

### Krok 1 — Zainstaluj Python 3

Pobierz Python 3.x z oficjalnej strony: **https://www.python.org/downloads/**

> **Ważne:** podczas instalacji zaznacz opcję „**Add Python to PATH**".

### Krok 2 — Zbuduj plik EXE

1. Kliknij dwukrotnie plik **`build_windows.bat`**.
2. Skrypt automatycznie:
   - zainstaluje zależności (Pillow, PyQt5, exifread, PyInstaller),
   - skompiluje aplikację do folderu `dist\KatalogZdjec\`,
   - opcjonalnie zbuduje instalator `.exe` (jeśli zainstalowano Inno Setup).

### Krok 3 — Uruchom lub zainstaluj

**Wersja przenośna (bez instalacji):**
```
dist\KatalogZdjec\KatalogZdjec.exe
```

**Instalator Windows** (wymaga Inno Setup 6.x — https://jrsoftware.org/isinfo.php):
```
dist\installer\KatalogZdjec_Instalator_v1.0.exe
```
Uruchom plik instalatora i postępuj zgodnie z instrukcjami kreatora.

---

## Pierwsze uruchomienie

1. Po uruchomieniu aplikacja zapyta o **folder katalogu** — wskaż dowolny folder na dysku, w którym chcesz przechowywać posortowane zdjęcia.
2. Aplikacja automatycznie przeskanuje wskazany folder i wypełni bazę danych.
3. Wybrany folder jest zapamiętywany — przy kolejnym uruchomieniu otworzy się automatycznie.

---

## Obsługa aplikacji

### Panel lewy — Drzewo folderów

- Wyświetla strukturę **Rok → Tydzień** na podstawie dat EXIF zdjęć.
- Kliknij na tydzień, aby zobaczyć miniatury zdjęć z tego okresu.
- Kliknij **prawym przyciskiem myszy** na tydzień lub rok, aby go usunąć.
- Przycisk **„Porządkuj zdjęcia"** — kopiuje zdjęcia do podfolderów rok/tydzień.

### Panel prawy — Siatka miniatur

- Wyświetla miniatury zdjęć z wybranego tygodnia.
- Kliknij miniaturę, aby otworzyć podgląd pełnego zdjęcia.
- **Sortowanie:** ustaw kolejność po dacie lub nazwie pliku (rosnąco / malejąco).

### Przeglądarka zdjęć

- Strzałki `←` / `→` — poprzednie / następne zdjęcie.
- Kółko myszy — powiększanie i pomniejszanie.
- Przycisk **GPS** — otwiera lokalizację zdjęcia w przeglądarce (OpenStreetMap).
- Przycisk **Usuń** — trwale usuwa zdjęcie z dysku i bazy danych.

### Import zdjęć

| Opcja                          | Opis                                              |
|--------------------------------|---------------------------------------------------|
| **Plik → Importuj z urządzenia** (`Ctrl+I`) | Import wielu zdjęć z folderu (aparat, USB, karta SD) |
| **Plik → Importuj pojedyncze zdjęcie** (`Ctrl+Shift+I`) | Wybierz jeden lub kilka plików ręcznie |

Po imporcie aplikacja automatycznie skanuje i porządkuje nowe zdjęcia.

> **Duplikaty:** aplikacja wykrywa pliki o tej samej nazwie i pyta, czy je pominąć czy zaimportować ponownie.

### Wygląd

Przełącz między jasnym a ciemnym interfejsem: **Widok → Jasny / Ciemny interfejs**.
Wybór jest zapamiętywany między sesjami.

---

## Skróty klawiszowe

| Skrót           | Działanie                        |
|-----------------|----------------------------------|
| `Ctrl+O`        | Otwórz folder katalogu           |
| `Ctrl+I`        | Importuj z urządzenia            |
| `Ctrl+Shift+I`  | Importuj pojedyncze zdjęcie      |
| `F5`            | Skanuj katalog ponownie          |
| `Ctrl+Q`        | Zakończ aplikację                |
| `←` / `→`       | Poprzednie / następne zdjęcie    |
| Kółko myszy     | Powiększenie w przeglądarce      |

---

## Odinstalowanie

### Linux

```bash
bash install_linux.sh --uninstall
```

Usuwa pliki aplikacji, skrypt uruchamiający i wpis w menu.
Folder katalogu ze zdjęciami **nie jest usuwany**.

### Windows

Otwórz **Panel sterowania → Programy → Odinstaluj program** i wybierz „Katalog Zdjęć".
Folder katalogu ze zdjęciami **nie jest usuwany**.

---

## Autor

**Marek Zettel** — <https://zetmar.net.pl>
