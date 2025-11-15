#!/bin/bash

# Installationsskript für den yabridge-updater
# Dieses Skript installiert die notwendigen Abhängigkeiten und das Hauptskript.

set -e # Bricht das Skript bei einem Fehler sofort ab.

# --- Konfiguration ---
SCRIPT_NAME="yabridge_updater.py"
INSTALL_NAME="yabridge-updater"
INSTALL_PATH="/usr/local/bin"

# --- UI / Farben ---
C_RED='\033[0;31m'
C_GREEN='\033[0;32m'
C_YELLOW='\033[0;33m'
C_BLUE='\033[0;34m'
C_BOLD='\033[1m'
C_RESET='\033[0m'

info() {
    echo -e "${C_BLUE}${C_BOLD}==>${C_RESET}${C_BOLD} $1${C_RESET}"
}

success() {
    echo -e "${C_GREEN}✓ $1${C_RESET}"
}

error() {
    echo -e "${C_RED}✗ FEHLER: $1${C_RESET}" >&2
    exit 1
}

warning() {
    echo -e "${C_YELLOW}WARNUNG: $1${C_RESET}"
}

# --- Hauptlogik ---

main() {
    info "Starte die Installation von '$INSTALL_NAME'..."

    # 1. Prüfen, ob das Skript mit Root-Rechten ausgeführt wird
    if [ "$(id -u)" -ne 0 ]; then
        error "Dieses Skript muss mit sudo oder als root ausgeführt werden. Beispiel: sudo ./install.sh"
    fi

    # 2. Prüfen, ob die Quelldatei existiert
    if [ ! -f "$SCRIPT_NAME" ]; then
        error "Die Skriptdatei '$SCRIPT_NAME' wurde nicht im selben Verzeichnis gefunden."
    fi

    # 3. Paketmanager erkennen und Abhängigkeiten installieren
    info "Erkenne Paketmanager und installiere Abhängigkeiten..."
    
    PKG_MANAGER=""
    if command -v apt-get &>/dev/null; then
        PKG_MANAGER="apt"
        info "Debian/Ubuntu-basiertes System erkannt (apt)."
        apt-get update
        apt-get install -y python3 python3-pip git openssl libsecret-tools python3-requests wine
    elif command -v dnf &>/dev/null; then
        PKG_MANAGER="dnf"
        info "Fedora/RHEL-basiertes System erkannt (dnf)."
        dnf install -y python3 python3-pip git openssl libsecret python3-requests wine
    elif command -v pacman &>/dev/null; then
        PKG_MANAGER="pacman"
        info "Arch-basiertes System erkannt (pacman)."
        pacman -Sy --noconfirm python python-pip git openssl libsecret python-requests wine
    elif command -v zypper &>/dev/null; then
        PKG_MANAGER="zypper"
        info "openSUSE-basiertes System erkannt (zypper)."
        zypper install -y python3 python3-pip git openssl libsecret-tools python3-requests wine
    else
        error "Konnte keinen unterstützten Paketmanager (apt, dnf, pacman, zypper) finden."
    fi

    success "Systemabhängigkeiten erfolgreich installiert."

    # 4. Das Skript nach /usr/local/bin kopieren
    info "Installiere das Skript nach '$INSTALL_PATH/$INSTALL_NAME'..."
    if cp "$SCRIPT_NAME" "$INSTALL_PATH/$INSTALL_NAME"; then
        success "Skript erfolgreich kopiert."
    else
        error "Kopieren des Skripts nach '$INSTALL_PATH' fehlgeschlagen."
    fi

    # 5. Shebang anpassen, um den System-Python-Interpreter zu verwenden
    info "Passe Shebang an, um explizit /usr/bin/python3 zu verwenden..."
    sed -i "1s|.*|#!/usr/bin/python3|" "$INSTALL_PATH/$INSTALL_NAME"

    # 6. Ausführrechte setzen
    info "Setze Ausführrechte..."
    if chmod 755 "$INSTALL_PATH/$INSTALL_NAME"; then
        success "Ausführrechte erfolgreich gesetzt."
    else
        error "Setzen der Ausführrechte fehlgeschlagen."
    fi

    echo
    success "Installation abgeschlossen!"
    info "Du kannst das Skript jetzt von überall mit dem Befehl '$INSTALL_NAME' ausführen."

    # 7. Den Updater zum ersten Mal ausführen (als der ursprüngliche Benutzer)
    info "Führe den Updater zum ersten Mal aus, um yabridge zu installieren..."
    if [ -z "$SUDO_USER" ]; then
        warning "Konnte den ursprünglichen Benutzer nicht ermitteln. Bitte führe den Updater manuell aus:"
        warning "  $INSTALL_NAME"
        exit 0
    fi

    if [ -n "$1" ]; then
        info "Verwende benutzerdefinierten Pfad: $1"
        sudo -u "$SUDO_USER" "$INSTALL_PATH/$INSTALL_NAME" --install-path "$1"
    else
        sudo -u "$SUDO_USER" "$INSTALL_PATH/$INSTALL_NAME"
    fi
}

# Skriptausführung starten
main
