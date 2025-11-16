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

remove_path_from_shell_configs() {
    local user_home=$1
    local yabridge_install_dir=$2

    if [ -z "$user_home" ] || [ -z "$yabridge_install_dir" ]; then
        return
    fi

    info "Suche nach Shell-Konfigurationen, um den PATH-Eintrag zu entfernen..."

    # Array von Shell-Konfigurationsdateien
    local shell_configs=("$user_home/.bashrc" "$user_home/.zshrc" "$user_home/.config/fish/config.fish")
    local marker_comment="# Added by yabridge-updater"
    local found=false

    for config_file in "${shell_configs[@]}"; do
        if [ -f "$config_file" ] && grep -q "$marker_comment" "$config_file"; then
            info "Entferne yabridge-updater PATH-Eintrag aus '$config_file'..."
            # Erstellt eine temporäre Datei ohne den Block und ersetzt dann die Originaldatei
            # Dies ist sicherer als sed -i, da es keine Probleme mit Berechtigungen unter sudo hat
            sed "/${marker_comment}/,+1d" "$config_file" > "${config_file}.tmp"
            # Berechtigungen und Eigentümer von der Originaldatei übernehmen
            chown --reference="$config_file" "${config_file}.tmp"
            chmod --reference="$config_file" "${config_file}.tmp"
            mv "${config_file}.tmp" "$config_file"
            success "PATH-Eintrag entfernt."
            found=true
        fi
    done
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
        PATH_CONFIG_FILE="$CONFIG_DIR/path"

        # Installationspfad ermitteln (benutzerdefiniert oder Standard)
        if [ -f "$PATH_CONFIG_FILE" ] && [ -s "$PATH_CONFIG_FILE" ]; then
            YABRIDGE_INSTALL_DIR=$(cat "$PATH_CONFIG_FILE")
            info "Benutzerdefinierter Installationspfad gefunden: $YABRIDGE_INSTALL_DIR"
        else
            YABRIDGE_INSTALL_DIR="$USER_HOME/.local/share/yabridge"
        fi

        # Backup-Pfad ableiten
        YABRIDGE_PARENT_DIR=$(dirname "$YABRIDGE_INSTALL_DIR")
        BACKUP_DIR="$YABRIDGE_PARENT_DIR/yabridge-backups"

        echo
        if [ -d "$CONFIG_DIR" ]; then
            read -p "$(echo -e "${C_YELLOW}Sollen die Konfigurationsdateien in '$CONFIG_DIR' gelöscht werden? (j/N) ${C_RESET}")" -r
            if [[ $REPLY =~ ^[JjYy]([Aa][Ss])?$ ]]; then
                info "Lösche Konfigurationsverzeichnis..."
                rm -rf "$CONFIG_DIR"
                success "Konfiguration gelöscht."
            fi
        fi

        if [ -d "$YABRIDGE_INSTALL_DIR" ] || [ -d "$BACKUP_DIR" ]; then
            read -p "$(echo -e "${C_YELLOW}Sollen die yabridge-Installation ('$YABRIDGE_INSTALL_DIR') und die Backups ('$BACKUP_DIR') gelöscht werden? (j/N) ${C_RESET}")" -r
            if [[ $REPLY =~ ^[JjYy]([Aa][Ss])?$ ]]; then
                info "Lösche yabridge-Installations- und Backup-Verzeichnisse..."
                rm -rf "$YABRIDGE_INSTALL_DIR" "$BACKUP_DIR"
                success "yabridge-Daten gelöscht."
            fi
        fi
    fi

    # 5. PATH-Eintrag aus Shell-Konfigurationen entfernen
    remove_path_from_shell_configs "$USER_HOME" "$YABRIDGE_INSTALL_DIR"

    echo
    success "Deinstallation abgeschlossen!"
    info "Möglicherweise musst du dein Terminal neu starten, damit die PATH-Änderungen wirksam werden."
}

main