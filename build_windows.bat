@echo off
chcp 65001 >nul 2>&1
setlocal EnableDelayedExpansion

rem Przejdź do katalogu w którym leży ten plik .bat
cd /d "%~dp0"

rem =============================================================================
rem  Skrypt budowania instalatora „Katalog Zdjęć" dla systemu Windows
rem  Wymagania: Python 3.8+, pip, (opcjonalnie) Inno Setup 6.x
rem
rem  Użycie: Kliknij dwukrotnie build_windows.bat  LUB  uruchom z terminala
rem =============================================================================

echo.
echo ============================================================
echo   Budowanie „Katalog Zdjęć" dla systemu Windows
echo ============================================================
echo.

rem --------------------------------------------------------------------------
rem  1. Sprawdzenie Python
rem --------------------------------------------------------------------------
echo [1/5] Sprawdzanie instalacji Python...
python --version >nul 2>&1
if errorlevel 1 (
    echo.
    echo  BLAD: Python nie jest zainstalowany lub nie jest w PATH.
    echo  Pobierz Python 3.x z:  https://www.python.org/downloads/
    echo  Upewnij sie, ze zaznaczylas "Add Python to PATH" podczas instalacji.
    echo.
    pause
    exit /b 1
)
for /f "tokens=*" %%v in ('python --version 2^>^&1') do set PY_VER=%%v
echo  Znaleziono: %PY_VER%
echo.

rem --------------------------------------------------------------------------
rem  2. Aktualizacja pip i instalacja zależności
rem --------------------------------------------------------------------------
echo [2/5] Instalowanie zaleznosci Python...
python -m pip install --upgrade pip --quiet
if errorlevel 1 (
    echo  BLAD: Nie mozna zaktualizowac pip.
    pause
    exit /b 1
)

python -m pip install --quiet "Pillow>=10.0" "PyQt5>=5.15" "exifread>=3.0"
if errorlevel 1 (
    echo  BLAD: Instalacja pakietow Python nie powiodla sie.
    pause
    exit /b 1
)
echo  Zaleznosci zainstalowane.
echo.

rem --------------------------------------------------------------------------
rem  3. Instalacja PyInstaller
rem --------------------------------------------------------------------------
echo [3/5] Instalowanie PyInstaller...
python -m pip install --quiet pyinstaller
if errorlevel 1 (
    echo  BLAD: Instalacja PyInstaller nie powiodla sie.
    pause
    exit /b 1
)
echo  PyInstaller zainstalowany.
echo.

rem --------------------------------------------------------------------------
rem  4. Budowanie EXE za pomocą PyInstaller
rem --------------------------------------------------------------------------
echo [4/5] Budowanie pliku EXE (moze chwile potrwac)...
echo.

if exist "dist\KatalogZdjec" (
    echo  Czyszczenie poprzedniej kompilacji...
    rmdir /s /q "dist\KatalogZdjec" >nul 2>&1
)
if exist "build\KatalogZdjec" (
    rmdir /s /q "build\KatalogZdjec" >nul 2>&1
)

python -m PyInstaller photo_catalog.spec --noconfirm
if errorlevel 1 (
    echo.
    echo  BLAD: PyInstaller nie mogl zbudowac aplikacji.
    echo  Sprawdz bledy powyzej i upewnij sie, ze plik photo_catalog.spec istnieje.
    echo.
    pause
    exit /b 1
)

if not exist "dist\KatalogZdjec\KatalogZdjec.exe" (
    echo  BLAD: Plik EXE nie zostal utworzony.
    pause
    exit /b 1
)
echo.
echo  Plik EXE utworzony: dist\KatalogZdjec\KatalogZdjec.exe
echo.

rem --------------------------------------------------------------------------
rem  5. Budowanie instalatora Inno Setup (opcjonalne)
rem --------------------------------------------------------------------------
echo [5/5] Szukanie Inno Setup...

set ISCC_PATH=""
for %%p in (
    "%ProgramFiles(x86)%\Inno Setup 6\ISCC.exe"
    "%ProgramFiles%\Inno Setup 6\ISCC.exe"
    "%LOCALAPPDATA%\Programs\Inno Setup 6\ISCC.exe"
    "C:\InnoSetup\ISCC.exe"
) do (
    if exist %%p (
        set ISCC_PATH=%%p
        goto :found_iscc
    )
)

echo  Inno Setup nie zostalo znalezione.
echo  Aby zbudowac instalator .exe:
echo    1. Pobierz Inno Setup 6: https://jrsoftware.org/isinfo.php
echo    2. Uruchom ponownie ten skrypt LUB skompiluj recznie:
echo       iscc installer_windows.iss
echo.
goto :summary

:found_iscc
echo  Znaleziono Inno Setup: %ISCC_PATH%
echo  Budowanie instalatora...
mkdir "dist\installer" >nul 2>&1
%ISCC_PATH% installer_windows.iss
if errorlevel 1 (
    echo  BLAD: Inno Setup nie mogl zbudowac instalatora.
) else (
    echo  Instalator gotowy: dist\installer\KatalogZdjec_Instalator_v1.0.exe
)
echo.

:summary
echo ============================================================
echo   Podsumowanie
echo ============================================================
echo.
echo   Folder aplikacji (przenoszalny):
echo     dist\KatalogZdjec\KatalogZdjec.exe
echo.
if exist "dist\installer\KatalogZdjec_Instalator_v1.0.exe" (
    echo   Instalator Windows:
    echo     dist\installer\KatalogZdjec_Instalator_v1.0.exe
    echo.
)
echo   Aby przetestowac aplikacje:
echo     dist\KatalogZdjec\KatalogZdjec.exe
echo.
pause
endlocal
