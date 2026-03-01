#!/usr/bin/env bash
# =============================================================================
# Skrypt budowania AppImage dla „Katalog Zdjęć" (Linux x86_64)
# Wymagania: python3, PyInstaller, pip3, wget/curl
#
# Użycie:  bash build_appimage.sh
# Wynik:   releases/KatalogZdjec-x86_64.AppImage
# =============================================================================

set -euo pipefail

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
APP_NAME="KatalogZdjec"
APPDIR="$SCRIPT_DIR/build_appimage/${APP_NAME}.AppDir"
DIST_LINUX="$SCRIPT_DIR/dist_linux"
RELEASES_DIR="$SCRIPT_DIR/releases"
APPIMAGETOOL="$SCRIPT_DIR/build_appimage/appimagetool-x86_64.AppImage"

RED='\033[0;31m'; GREEN='\033[0;32m'; YELLOW='\033[1;33m'; BLUE='\033[0;34m'; NC='\033[0m'
info()    { echo -e "${BLUE}[INFO]${NC} $*"; }
success() { echo -e "${GREEN}[OK]${NC}   $*"; }
warn()    { echo -e "${YELLOW}[UWAGA]${NC} $*"; }
error()   { echo -e "${RED}[BŁĄD]${NC} $*" >&2; exit 1; }

echo
echo -e "${BLUE}================================================${NC}"
echo -e "${BLUE}  Budowanie AppImage — ${APP_NAME}             ${NC}"
echo -e "${BLUE}================================================${NC}"
echo

cd "$SCRIPT_DIR"

# --- 1. Sprawdzenie zależności -----------------------------------------------
info "Sprawdzanie zależności..."
command -v python3 &>/dev/null || error "Brak python3"
python3 -m PyInstaller --version &>/dev/null || \
    pip3 install pyinstaller --user --quiet --break-system-packages || \
    error "Nie można zainstalować PyInstaller"
success "Zależności OK"

# --- 2. Czyszczenie poprzedniej kompilacji ------------------------------------
info "Czyszczenie poprzedniej kompilacji..."
rm -rf "$DIST_LINUX" build_appimage
mkdir -p build_appimage "$RELEASES_DIR"

# --- 3. Budowanie binarki Linux przez PyInstaller ----------------------------
info "Budowanie binarki Linux (PyInstaller)..."
python3 -m PyInstaller photo_catalog.spec \
    --noconfirm \
    --distpath "$DIST_LINUX" \
    2>&1 | grep -E "^(INFO|WARNING|ERROR|Building)" || true

if [[ ! -f "$DIST_LINUX/$APP_NAME/$APP_NAME" ]]; then
    error "PyInstaller nie zbudował binarki: $DIST_LINUX/$APP_NAME/$APP_NAME"
fi
success "Binarka zbudowana: $(du -sh "$DIST_LINUX/$APP_NAME" | cut -f1)"

# --- 4. Tworzenie struktury AppDir -------------------------------------------
info "Tworzenie AppDir..."
mkdir -p "$APPDIR"

# Kopiuj pliki PyInstaller do AppDir
cp -r "$DIST_LINUX/$APP_NAME/." "$APPDIR/"

# AppRun — punkt wejścia AppImage
cat > "$APPDIR/AppRun" << 'APPRUN'
#!/usr/bin/env bash
HERE="$(dirname "$(readlink -f "${0}")")"
export QT_QPA_PLATFORM_PLUGIN_PATH="$HERE/PyQt5/Qt5/plugins/platforms"
export QT_PLUGIN_PATH="$HERE/PyQt5/Qt5/plugins"
exec "$HERE/KatalogZdjec" "$@"
APPRUN
chmod +x "$APPDIR/AppRun"

# Plik .desktop
cat > "$APPDIR/katalog-zdjec.desktop" << 'DESKTOP'
[Desktop Entry]
Version=1.0
Type=Application
Name=Katalog Zdjęć
GenericName=Przeglądarka zdjęć
Comment=Automatycznie sortuje zdjęcia do folderów rok/tydzień na podstawie EXIF
Exec=KatalogZdjec
Icon=katalog-zdjec
Terminal=false
StartupNotify=true
Categories=Graphics;Photography;Viewer;
Keywords=zdjęcia;katalog;foto;EXIF;galeria;
DESKTOP

# Ikona (AppImage wymaga pliku bez rozszerzenia w AppDir i jako katalog-zdjec.svg)
if [[ -f "$SCRIPT_DIR/resources/photo_catalog.svg" ]]; then
    cp "$SCRIPT_DIR/resources/photo_catalog.svg" "$APPDIR/katalog-zdjec.svg"
    success "Ikona SVG skopiowana"
else
    warn "Brak ikony SVG — AppImage będzie bez ikony"
fi

success "AppDir przygotowany"

# --- 5. Pobranie appimagetool ------------------------------------------------
if [[ ! -x "$APPIMAGETOOL" ]]; then
    info "Pobieranie appimagetool..."
    curl -L -o "$APPIMAGETOOL" \
        "https://github.com/AppImage/AppImageKit/releases/download/continuous/appimagetool-x86_64.AppImage"
    chmod +x "$APPIMAGETOOL"
    success "appimagetool pobrany"
fi

# --- 6. Budowanie AppImage ---------------------------------------------------
info "Budowanie AppImage..."
OUTPUT="$RELEASES_DIR/${APP_NAME}-x86_64.AppImage"

ARCH=x86_64 "$APPIMAGETOOL" --no-appstream "$APPDIR" "$OUTPUT" 2>&1 | \
    grep -v "^squashfs\|^mksquashfs" || true

if [[ ! -f "$OUTPUT" ]]; then
    error "Nie udało się zbudować AppImage"
fi

chmod +x "$OUTPUT"
success "AppImage gotowy: $OUTPUT ($(du -sh "$OUTPUT" | cut -f1))"

echo
echo -e "${GREEN}================================================${NC}"
echo -e "${GREEN}  Budowanie AppImage zakończone!               ${NC}"
echo -e "${GREEN}================================================${NC}"
echo
echo -e "  Plik: ${YELLOW}$OUTPUT${NC}"
echo -e "  Uruchom: ${YELLOW}chmod +x KatalogZdjec-x86_64.AppImage && ./KatalogZdjec-x86_64.AppImage${NC}"
echo
