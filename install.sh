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

# --- Internationalization (i18n) ---
LANG_CODE=${LANG%%.*} # z.B. de_DE.UTF-8 -> de_DE

# UI-Texte - werden je nach Sprache befüllt
MSG_START_INSTALL=""
MSG_ERR_NEED_ROOT=""
MSG_ERR_SCRIPT_NOT_FOUND=""
MSG_INFO_DETECT_PKG=""
MSG_INFO_DEBIAN_DETECTED=""
MSG_INFO_FEDORA_DETECTED=""
MSG_INFO_ARCH_DETECTED=""
MSG_INFO_SUSE_DETECTED=""
MSG_ERR_NO_PKG_MANAGER=""
MSG_SUCCESS_DEPS_INSTALLED=""
MSG_INFO_INSTALLING_SCRIPT=""
MSG_SUCCESS_SCRIPT_COPIED=""
MSG_ERR_COPY_FAILED=""
MSG_INFO_ADJUST_SHEBANG=""
MSG_INFO_SET_PERMS=""
MSG_SUCCESS_PERMS_SET=""
MSG_ERR_PERMS_FAILED=""
MSG_SUCCESS_INSTALL_COMPLETE=""
MSG_INFO_HOW_TO_RUN=""
MSG_INFO_FIRST_RUN=""
MSG_WARN_NO_SUDO_USER=""
MSG_WARN_RUN_MANUALLY=""
MSG_INFO_CUSTOM_PATH=""

if [[ "$LANG_CODE" == "de"* ]]; then
    MSG_START_INSTALL="Starte die Installation von"
    MSG_ERR_NEED_ROOT="Dieses Skript muss mit sudo oder als root ausgeführt werden. Beispiel: sudo ./install.sh"
    MSG_ERR_SCRIPT_NOT_FOUND="Die Skriptdatei '$SCRIPT_NAME' wurde nicht im selben Verzeichnis gefunden."
    MSG_INFO_DETECT_PKG="Erkenne Paketmanager und installiere Abhängigkeiten..."
    MSG_INFO_DEBIAN_DETECTED="Debian/Ubuntu-basiertes System erkannt (apt)."
    MSG_INFO_FEDORA_DETECTED="Fedora/RHEL-basiertes System erkannt (dnf)."
    MSG_INFO_ARCH_DETECTED="Arch-basiertes System erkannt (pacman)."
    MSG_INFO_SUSE_DETECTED="openSUSE-basiertes System erkannt (zypper)."
    MSG_ERR_NO_PKG_MANAGER="Konnte keinen unterstützten Paketmanager (apt, dnf, pacman, zypper) finden."
    MSG_SUCCESS_DEPS_INSTALLED="Systemabhängigkeiten erfolgreich installiert."
    MSG_INFO_INSTALLING_SCRIPT="Installiere das Skript nach"
    MSG_SUCCESS_SCRIPT_COPIED="Skript erfolgreich kopiert."
    MSG_ERR_COPY_FAILED="Kopieren des Skripts nach '$INSTALL_PATH' fehlgeschlagen."
    MSG_INFO_ADJUST_SHEBANG="Passe Shebang an, um explizit /usr/bin/python3 zu verwenden..."
    MSG_INFO_SET_PERMS="Setze Ausführrechte..."
    MSG_SUCCESS_PERMS_SET="Ausführrechte erfolgreich gesetzt."
    MSG_ERR_PERMS_FAILED="Setzen der Ausführrechte fehlgeschlagen."
    MSG_SUCCESS_INSTALL_COMPLETE="Installation abgeschlossen!"
    MSG_INFO_HOW_TO_RUN="Du kannst das Skript jetzt von überall mit dem Befehl '$INSTALL_NAME' ausführen."
    MSG_INFO_FIRST_RUN="Führe den Updater zum ersten Mal aus, um yabridge zu installieren..."
    MSG_WARN_NO_SUDO_USER="Konnte den ursprünglichen Benutzer nicht ermitteln. Bitte führe den Updater manuell aus:"
    MSG_WARN_RUN_MANUALLY="  $INSTALL_NAME"
    MSG_INFO_CUSTOM_PATH="Verwende benutzerdefinierten Pfad:"
else
    MSG_START_INSTALL="Starting the installation of"
    MSG_ERR_NEED_ROOT="This script must be run with sudo or as root. Example: sudo ./install.sh"
    MSG_ERR_SCRIPT_NOT_FOUND="The script file '$SCRIPT_NAME' was not found in the same directory."
    MSG_INFO_DETECT_PKG="Detecting package manager and installing dependencies..."
    MSG_INFO_DEBIAN_DETECTED="Debian/Ubuntu-based system detected (apt)."
    MSG_INFO_FEDORA_DETECTED="Fedora/RHEL-based system detected (dnf)."
    MSG_INFO_ARCH_DETECTED="Arch-based system detected (pacman)."
    MSG_INFO_SUSE_DETECTED="openSUSE-based system detected (zypper)."
    MSG_ERR_NO_PKG_MANAGER="Could not find a supported package manager (apt, dnf, pacman, zypper)."
    MSG_SUCCESS_DEPS_INSTALLED="System dependencies installed successfully."
    MSG_INFO_INSTALLING_SCRIPT="Installing the script to"
    MSG_SUCCESS_SCRIPT_COPIED="Script copied successfully."
    MSG_ERR_COPY_FAILED="Failed to copy the script to '$INSTALL_PATH'."
    MSG_INFO_ADJUST_SHEBANG="Adjusting shebang to use /usr/bin/python3 explicitly..."
    MSG_INFO_SET_PERMS="Setting execution permissions..."
    MSG_SUCCESS_PERMS_SET="Execution permissions set successfully."
    MSG_ERR_PERMS_FAILED="Failed to set execution permissions."
    MSG_SUCCESS_INSTALL_COMPLETE="Installation complete!"
    MSG_INFO_HOW_TO_RUN="You can now run the script from anywhere using the command '$INSTALL_NAME'."
    MSG_INFO_FIRST_RUN="Running the updater for the first time to install yabridge..."
    MSG_WARN_NO_SUDO_USER="Could not determine the original user. Please run the updater manually:"
    MSG_WARN_RUN_MANUALLY="  $INSTALL_NAME"
    MSG_INFO_CUSTOM_PATH="Using custom path:"
fi

# --- Hauptlogik ---

main() {
    info "${MSG_START_INSTALL} '$INSTALL_NAME'..."

    # 1. Prüfen, ob das Skript mit Root-Rechten ausgeführt wird
    if [ "$(id -u)" -ne 0 ]; then
        error "$MSG_ERR_NEED_ROOT"
    fi

    # 2. Prüfen, ob die Quelldatei existiert
    if [ ! -f "$SCRIPT_NAME" ]; then
        error "$MSG_ERR_SCRIPT_NOT_FOUND"
    fi

    # 3. Paketmanager erkennen und Abhängigkeiten installieren
    info "$MSG_INFO_DETECT_PKG"
    
    PKG_MANAGER=""
    if command -v apt-get &>/dev/null; then
        PKG_MANAGER="apt"
        info "$MSG_INFO_DEBIAN_DETECTED"
        apt-get update
        apt-get install -y python3 python3-pip git openssl libsecret-tools python3-requests wine
    elif command -v dnf &>/dev/null; then
        PKG_MANAGER="dnf"
        info "$MSG_INFO_FEDORA_DETECTED"
        dnf install -y python3 python3-pip git openssl libsecret python3-requests wine
    elif command -v pacman &>/dev/null; then
        PKG_MANAGER="pacman"
        info "$MSG_INFO_ARCH_DETECTED"
        pacman -Sy --noconfirm python python-pip git openssl libsecret python-requests wine
    elif command -v zypper &>/dev/null; then
        PKG_MANAGER="zypper"
        info "$MSG_INFO_SUSE_DETECTED"
        zypper install -y python3 python3-pip git openssl libsecret-tools python3-requests wine
    else
        error "$MSG_ERR_NO_PKG_MANAGER"
    fi

    success "$MSG_SUCCESS_DEPS_INSTALLED"

    # 4. Das Skript nach /usr/local/bin kopieren
    info "${MSG_INFO_INSTALLING_SCRIPT} '$INSTALL_PATH/$INSTALL_NAME'..."
    if cp "$SCRIPT_NAME" "$INSTALL_PATH/$INSTALL_NAME"; then
        success "$MSG_SUCCESS_SCRIPT_COPIED"
    else
        error "$MSG_ERR_COPY_FAILED"
    fi

    # 5. Shebang anpassen, um den System-Python-Interpreter zu verwenden
    info "$MSG_INFO_ADJUST_SHEBANG"
    sed -i "1s|.*|#!/usr/bin/python3|" "$INSTALL_PATH/$INSTALL_NAME"

    # 6. Ausführrechte setzen
    info "$MSG_INFO_SET_PERMS"
    if chmod 755 "$INSTALL_PATH/$INSTALL_NAME"; then
        success "$MSG_SUCCESS_PERMS_SET"
    else
        error "$MSG_ERR_PERMS_FAILED"
    fi

    echo
    success "$MSG_SUCCESS_INSTALL_COMPLETE"
    info "${MSG_INFO_HOW_TO_RUN}"

    # 7. Den Updater zum ersten Mal ausführen (als der ursprüngliche Benutzer)
    info "$MSG_INFO_FIRST_RUN"
    if [ -z "$SUDO_USER" ]; then
        warning "$MSG_WARN_NO_SUDO_USER"
        warning "$MSG_WARN_RUN_MANUALLY"
        exit 0
    fi

    if [ -n "$1" ]; then
        info "${MSG_INFO_CUSTOM_PATH} $1"
        sudo -u "$SUDO_USER" "$INSTALL_PATH/$INSTALL_NAME" --install-path "$1"
    else
        sudo -u "$SUDO_USER" "$INSTALL_PATH/$INSTALL_NAME"
    fi
}

# Skriptausführung starten
main
