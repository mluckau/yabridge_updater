#!/bin/bash

# Deinstallationsskript für den yabridge-updater

set -e

# --- Konfiguration ---
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

main() {
    info "Starte die Deinstallation von '$INSTALL_NAME'..."

    # 1. Prüfen, ob das Skript mit Root-Rechten ausgeführt wird
    if [ "$(id -u)" -ne 0 ]; then
        error "Dieses Skript muss mit sudo oder als root ausgeführt werden. Beispiel: sudo ./uninstall.sh"
    fi

    # 2. Den ursprünglichen Benutzer ermitteln
    if [ -n "$SUDO_USER" ]; then
        USER_HOME=$(getent passwd "$SUDO_USER" | cut -d: -f6)
    else
        warning "Konnte den ursprünglichen Benutzer nicht ermitteln. Einige Dateien müssen möglicherweise manuell gelöscht werden."
        USER_HOME=""
    fi

    # 3. Das Hauptskript entfernen
    if [ -f "$INSTALL_PATH/$INSTALL_NAME" ]; then
        info "Entferne das Hauptskript: $INSTALL_PATH/$INSTALL_NAME"
        rm -f "$INSTALL_PATH/$INSTALL_NAME"
        success "Hauptskript entfernt."
    else
        info "Hauptskript nicht gefunden. Übersprungen."
    fi

    # 4. Interaktiv weitere Daten löschen
    if [ -n "$USER_HOME" ]; then
        CONFIG_DIR="$USER_HOME/.config/yabridge-updater"
        YABRIDGE_DEFAULT_DIR="$USER_HOME/.local/share/yabridge"
        BACKUP_DEFAULT_DIR="$USER_HOME/.local/share/yabridge-backups"

        echo
        if [ -d "$CONFIG_DIR" ]; then
            read -p "$(echo -e "${C_YELLOW}Sollen die Konfigurationsdateien (inkl. Token) in '$CONFIG_DIR' gelöscht werden? (j/N) ${C_RESET}")" -r
            if [[ $REPLY =~ ^[JjYy]$ ]]; then
                info "Lösche Konfigurationsverzeichnis..."
                rm -rf "$CONFIG_DIR"
                success "Konfiguration gelöscht."
            fi
        fi

        read -p "$(echo -e "${C_YELLOW}Sollen die yabridge-Installation und die Backups gelöscht werden? (Dies kann nicht rückgängig gemacht werden!) (j/N) ${C_RESET}")" -r
        if [[ $REPLY =~ ^[JjYy]$ ]]; then
            info "Lösche yabridge-Installations- und Backup-Verzeichnisse..."
            # Hinweis: Dies löscht nur die Standardpfade. Benutzerdefinierte Pfade müssen manuell gelöscht werden.
            rm -rf "$YABRIDGE_DEFAULT_DIR" "$BACKUP_DEFAULT_DIR"
            success "yabridge-Daten gelöscht."
            warning "Falls du einen benutzerdefinierten Pfad verwendet hast, musst du diesen manuell löschen."
        fi
    fi

    echo
    success "Deinstallation abgeschlossen!"
    info "Bitte entferne die 'yabridge-updater'-Zeile manuell aus deiner Shell-Konfigurationsdatei (z.B. ~/.bashrc, ~/.zshrc)."
}

main