#!/usr/bin/env bash
# =============================================================================
# Instalator aplikacji „Katalog Zdjęć" dla systemu Linux (Debian / Ubuntu)
# =============================================================================
# Użycie:  bash install_linux.sh
#          bash install_linux.sh --uninstall
# =============================================================================

set -euo pipefail

APP_NAME="Katalog Zdjęć"
APP_ID="katalog-zdjec"
APP_DIR="$HOME/.local/share/$APP_ID"
BIN_DIR="$HOME/.local/bin"
LAUNCHER="$BIN_DIR/$APP_ID"
DESKTOP_FILE="$HOME/.local/share/applications/$APP_ID.desktop"
ICON_DIR="$HOME/.local/share/icons/hicolor/scalable/apps"
ICON_FILE="$ICON_DIR/$APP_ID.svg"
CONFIG_FILE="$HOME/.config/PhotoCatalog/PhotoCatalog.conf"
SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"

# --------------------------------------------------------------------------- #
#  Kolory terminala
# --------------------------------------------------------------------------- #
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
BLUE='\033[0;34m'
NC='\033[0m'

info()    { echo -e "${BLUE}[INFO]${NC} $*"; }
success() { echo -e "${GREEN}[OK]${NC}   $*"; }
warn()    { echo -e "${YELLOW}[UWAGA]${NC} $*"; }
error()   { echo -e "${RED}[BŁĄD]${NC} $*" >&2; }

# --------------------------------------------------------------------------- #
#  Odinstalowanie
# --------------------------------------------------------------------------- #
uninstall() {
    echo
    echo -e "${BLUE}=== Odinstalowywanie aplikacji ${APP_NAME} ===${NC}"
    echo

    # --- Pytanie o zdjęcia (PRZED usunięciem aplikacji) ---
    CATALOG_ROOT=""
    if [[ -f "$CONFIG_FILE" ]]; then
        CATALOG_ROOT=$(grep -m1 "^catalog_root=" "$CONFIG_FILE" 2>/dev/null | sed 's/^catalog_root=//' | tr -d '\r\n')
    fi

    if [[ -n "$CATALOG_ROOT" && -d "$CATALOG_ROOT" ]]; then
        echo -e "${YELLOW}Znaleziono katalog ze zdjęciami: $CATALOG_ROOT${NC}"
        echo
        echo -e "${RED}UWAGA: Ta operacja jest nieodwracalna!${NC}"
        read -r -p "Czy usunąć WSZYSTKIE zdjęcia z katalogu? (t/N): " DEL_PHOTOS
        if [[ "$DEL_PHOTOS" == "t" || "$DEL_PHOTOS" == "T" ]]; then
            read -r -p "Jesteś pewien? Wpisz TAK aby potwierdzić: " CONFIRM
            if [[ "$CONFIRM" == "TAK" ]]; then
                warn "Usuwanie zdjęć z: $CATALOG_ROOT ..."
                rm -rf "$CATALOG_ROOT"
                success "Katalog ze zdjęciami usunięty."
            else
                info "Anulowano — zdjęcia pozostają nienaruszone."
            fi
        else
            info "Zdjęcia pozostają nienaruszone w: $CATALOG_ROOT"
        fi
    else
        info "Zdjęcia nie są zarządzane przez instalator — pozostają bez zmian."
    fi

    echo

    # --- Usunięcie plików aplikacji ---
    rm -rf "$APP_DIR"           && info "Usunięto katalog aplikacji: $APP_DIR"
    rm -f  "$LAUNCHER"          && info "Usunięto skrypt uruchamiający: $LAUNCHER"
    rm -f  "$DESKTOP_FILE"      && info "Usunięto plik .desktop"
    rm -f  "$ICON_FILE"         && info "Usunięto ikonę aplikacji"
    rm -rf "$HOME/.config/PhotoCatalog" && info "Usunięto konfigurację aplikacji"
    update-desktop-database "$HOME/.local/share/applications" 2>/dev/null || true
    gtk-update-icon-cache "$HOME/.local/share/icons/hicolor" 2>/dev/null || true

    echo
    success "Odinstalowanie zakończone."
}

if [[ "${1:-}" == "--uninstall" ]]; then
    uninstall
    exit 0
fi

# --------------------------------------------------------------------------- #
#  Instalacja
# --------------------------------------------------------------------------- #
echo
echo -e "${BLUE}================================================${NC}"
echo -e "${BLUE}  Instalacja aplikacji ${APP_NAME}             ${NC}"
echo -e "${BLUE}================================================${NC}"
echo

# --- 1. Sprawdzenie Python 3 ------------------------------------------------
info "Sprawdzanie wersji Python 3..."
if ! command -v python3 &>/dev/null; then
    error "Python 3 nie jest zainstalowany."
    error "Zainstaluj go: sudo apt install python3"
    exit 1
fi
PY_VER=$(python3 -c 'import sys; print(".".join(map(str, sys.version_info[:2])))')
info "Znaleziono Python $PY_VER"
if python3 -c 'import sys; exit(0 if sys.version_info >= (3,8) else 1)'; then
    success "Wersja Pythona jest wystarczająca (>= 3.8)."
else
    error "Wymagany Python 3.8 lub nowszy. Masz Python $PY_VER."
    exit 1
fi

# --- 2. Instalacja zależności systemowych -----------------------------------
info "Instalowanie zależności systemowych (może wymagać hasła sudo)..."

# Sprawdź menedżer pakietów
if command -v apt-get &>/dev/null; then
    sudo apt-get update -qq
    sudo apt-get install -y \
        python3-pip \
        python3-pyqt5 \
        python3-pil \
        python3-exifread 2>/dev/null || \
    sudo apt-get install -y \
        python3-pip \
        python3-pyqt5 \
        python3-pil
    success "Pakiety systemowe zainstalowane."
elif command -v dnf &>/dev/null; then
    sudo dnf install -y python3-pip python3-qt5 python3-pillow
    success "Pakiety systemowe zainstalowane (dnf)."
elif command -v pacman &>/dev/null; then
    sudo pacman -S --noconfirm python-pip python-pyqt5 python-pillow
    success "Pakiety systemowe zainstalowane (pacman)."
else
    warn "Nieznany menedżer pakietów. Upewnij się, że masz zainstalowane:"
    warn "  python3-pip, PyQt5, Pillow, exifread"
fi

# --- 3. Instalacja pakietów pip (tylko jeśli nie są dostępne przez apt) ----
info "Sprawdzanie dostępności pakietów Python..."
NEED_PIP=false
python3 -c "import PyQt5" 2>/dev/null   || NEED_PIP=true
python3 -c "import PIL"   2>/dev/null   || NEED_PIP=true
python3 -c "import exifread" 2>/dev/null || NEED_PIP=true

if $NEED_PIP; then
    info "Instalowanie brakujących pakietów Python (pip)..."
    # Spróbuj --user, a w razie blokady PEP 668 użyj --break-system-packages
    pip3 install --user --quiet \
        "Pillow>=10.0" "PyQt5>=5.15" "exifread>=3.0" 2>/dev/null || \
    pip3 install --user --quiet --break-system-packages \
        "Pillow>=10.0" "PyQt5>=5.15" "exifread>=3.0" 2>/dev/null || \
    warn "Pip nie mógł zainstalować pakietów — zostaną użyte wersje systemowe."
    success "Pakiety pip przetworzone."
else
    success "Wszystkie pakiety Python są już dostępne (przez apt)."
fi

# --- 4. Kopiowanie plików aplikacji ----------------------------------------
info "Kopiowanie plików aplikacji do: $APP_DIR"
mkdir -p "$APP_DIR"

# Kopiuj pliki projektu (bez katalogu tests i cache)
rsync -a --exclude='__pycache__' \
         --exclude='*.pyc' \
         --exclude='.pytest_cache' \
         --exclude='tests' \
         --exclude='install_linux.sh' \
         "$SCRIPT_DIR/" "$APP_DIR/" 2>/dev/null || \
cp -r "$SCRIPT_DIR/." "$APP_DIR/"

success "Pliki aplikacji skopiowane."

# --- 5. Tworzenie skryptu uruchamiającego ----------------------------------
info "Tworzenie skryptu uruchamiającego..."
mkdir -p "$BIN_DIR"

cat > "$LAUNCHER" << EOF
#!/usr/bin/env bash
# Skrypt uruchamiający „Katalog Zdjęć"
exec python3 "$APP_DIR/main.py" "\$@"
EOF
chmod +x "$LAUNCHER"
success "Skrypt uruchamiający: $LAUNCHER"

# --- 6. Dodanie do PATH (jeśli potrzeba) -----------------------------------
if [[ ":$PATH:" != *":$BIN_DIR:"* ]]; then
    warn "Katalog $BIN_DIR nie jest w PATH."
    SHELL_RC="$HOME/.bashrc"
    [[ "$SHELL" == */zsh ]] && SHELL_RC="$HOME/.zshrc"
    echo "" >> "$SHELL_RC"
    echo "# Katalog Zdjęć" >> "$SHELL_RC"
    echo 'export PATH="$HOME/.local/bin:$PATH"' >> "$SHELL_RC"
    warn "Dodano wpis do $SHELL_RC. Uruchom ponownie terminal lub wpisz:"
    warn "  source $SHELL_RC"
fi

# --- 7. Instalacja ikony aplikacji ------------------------------------------
info "Instalowanie ikony aplikacji..."
mkdir -p "$ICON_DIR"
if [[ -f "$APP_DIR/resources/photo_catalog.svg" ]]; then
    cp "$APP_DIR/resources/photo_catalog.svg" "$ICON_FILE"
    gtk-update-icon-cache "$HOME/.local/share/icons/hicolor" 2>/dev/null || true
    success "Ikona zainstalowana: $ICON_FILE"
else
    warn "Nie znaleziono pliku ikony — zostanie użyta ikona systemowa."
    ICON_FILE="image-viewer"
fi

# --- 8. Tworzenie pliku .desktop -------------------------------------------
info "Tworzenie wpisu w menu aplikacji..."
mkdir -p "$HOME/.local/share/applications"

cat > "$DESKTOP_FILE" << EOF
[Desktop Entry]
Version=1.0
Type=Application
Name=Katalog Zdjęć
GenericName=Przeglądarka zdjęć
Comment=Automatycznie sortuje zdjęcia do folderów rok/tydzień na podstawie EXIF
Exec=$LAUNCHER
Icon=$ICON_FILE
Terminal=false
StartupNotify=true
Categories=Graphics;Photography;Viewer;
Keywords=zdjęcia;katalog;foto;EXIF;galeria;
EOF

update-desktop-database "$HOME/.local/share/applications" 2>/dev/null || true
success "Wpis w menu aplikacji dodany."

# --------------------------------------------------------------------------- #
#  Podsumowanie
# --------------------------------------------------------------------------- #
echo
echo -e "${GREEN}================================================${NC}"
echo -e "${GREEN}  Instalacja zakończona pomyślnie!              ${NC}"
echo -e "${GREEN}================================================${NC}"
echo
echo -e "  Uruchom aplikację:"
echo -e "    ${YELLOW}$APP_ID${NC}           (z terminala)"
echo -e "    lub znajdź ${YELLOW}Katalog Zdjęć${NC} w menu aplikacji"
echo
echo -e "  Odinstaluj:"
echo -e "    ${YELLOW}bash $SCRIPT_DIR/install_linux.sh --uninstall${NC}"
echo
