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

# --- Internationalization (i18n) ---
LANG_CODE=${LANG%%.*} # z.B. de_DE.UTF-8 -> de_DE

# UI-Texte
MSG_START_UNINSTALL=""
MSG_ERR_NEED_ROOT=""
MSG_WARN_NO_SUDO_USER=""
MSG_INFO_REMOVE_MAIN_SCRIPT=""
MSG_SUCCESS_MAIN_SCRIPT_REMOVED=""
MSG_INFO_MAIN_SCRIPT_NOT_FOUND=""
MSG_INFO_CUSTOM_PATH_FOUND=""
MSG_PROMPT_DELETE_CONFIG=""
MSG_INFO_DELETING_CONFIG=""
MSG_SUCCESS_CONFIG_DELETED=""
MSG_PROMPT_DELETE_YABRIDGE_DATA=""
MSG_INFO_DELETING_YABRIDGE_DATA=""
MSG_SUCCESS_YABRIDGE_DATA_DELETED=""
MSG_INFO_SEARCHING_SHELL_CONFIGS=""
MSG_INFO_REMOVING_PATH_ENTRY=""
MSG_SUCCESS_PATH_ENTRY_REMOVED=""
MSG_SUCCESS_UNINSTALL_COMPLETE=""
MSG_INFO_RESTART_TERMINAL=""
MSG_INFO_DOWNLOADING_SCRIPT=""
MSG_ERR_DOWNLOAD_FAILED=""
MSG_ERR_NO_DOWNLOAD_TOOL=""

if [[ "$LANG_CODE" == "de"* ]]; then
    MSG_START_UNINSTALL="Starte die Deinstallation von"
    MSG_ERR_NEED_ROOT="Dieses Skript muss mit sudo oder als root ausgeführt werden. Beispiel: sudo ./uninstall.sh"
    MSG_WARN_NO_SUDO_USER="Konnte den ursprünglichen Benutzer nicht ermitteln. Einige Dateien müssen möglicherweise manuell gelöscht werden."
    MSG_INFO_REMOVE_MAIN_SCRIPT="Entferne das Hauptskript:"
    MSG_SUCCESS_MAIN_SCRIPT_REMOVED="Hauptskript entfernt."
    MSG_INFO_MAIN_SCRIPT_NOT_FOUND="Hauptskript nicht gefunden. Übersprungen."
    MSG_INFO_CUSTOM_PATH_FOUND="Benutzerdefinierter Installationspfad gefunden:"
    MSG_PROMPT_DELETE_CONFIG="Sollen die Konfigurationsdateien in '%s' gelöscht werden? (j/N) "
    MSG_INFO_DELETING_CONFIG="Lösche Konfigurationsverzeichnis..."
    MSG_SUCCESS_CONFIG_DELETED="Konfiguration gelöscht."
    MSG_PROMPT_DELETE_YABRIDGE_DATA="Sollen die yabridge-Installation ('%s') und die Backups ('%s') gelöscht werden? (j/N) "
    MSG_INFO_DELETING_YABRIDGE_DATA="Lösche yabridge-Installations- und Backup-Verzeichnisse..."
    MSG_SUCCESS_YABRIDGE_DATA_DELETED="yabridge-Daten gelöscht."
    MSG_INFO_SEARCHING_SHELL_CONFIGS="Suche nach Shell-Konfigurationen, um den PATH-Eintrag zu entfernen..."
    MSG_INFO_REMOVING_PATH_ENTRY="Entferne yabridge-updater PATH-Eintrag aus"
    MSG_SUCCESS_PATH_ENTRY_REMOVED="PATH-Eintrag entfernt."
    MSG_SUCCESS_UNINSTALL_COMPLETE="Deinstallation abgeschlossen!"
    MSG_INFO_RESTART_TERMINAL="Möglicherweise musst du dein Terminal neu starten, damit die PATH-Änderungen wirksam werden."
    MSG_INFO_DOWNLOADING_SCRIPT="Lade '${SCRIPT_NAME}' von GitHub herunter..."
    MSG_ERR_DOWNLOAD_FAILED="Herunterladen von '${SCRIPT_NAME}' fehlgeschlagen."
    MSG_ERR_NO_DOWNLOAD_TOOL="Zum Herunterladen wird 'curl' oder 'wget' benötigt, wurde aber nicht gefunden."
else
    MSG_START_UNINSTALL="Starting the uninstallation of"
    MSG_ERR_NEED_ROOT="This script must be run with sudo or as root. Example: sudo ./uninstall.sh"
    MSG_WARN_NO_SUDO_USER="Could not determine the original user. Some files may need to be deleted manually."
    MSG_INFO_REMOVE_MAIN_SCRIPT="Removing the main script:"
    MSG_SUCCESS_MAIN_SCRIPT_REMOVED="Main script removed."
    MSG_INFO_MAIN_SCRIPT_NOT_FOUND="Main script not found. Skipped."
    MSG_INFO_CUSTOM_PATH_FOUND="Custom installation path found:"
    MSG_PROMPT_DELETE_CONFIG="Delete configuration files in '%s'? (y/N) "
    MSG_INFO_DELETING_CONFIG="Deleting configuration directory..."
    MSG_SUCCESS_CONFIG_DELETED="Configuration deleted."
    MSG_PROMPT_DELETE_YABRIDGE_DATA="Delete the yabridge installation ('%s') and backups ('%s')? (y/N) "
    MSG_INFO_DELETING_YABRIDGE_DATA="Deleting yabridge installation and backup directories..."
    MSG_SUCCESS_YABRIDGE_DATA_DELETED="yabridge data deleted."
    MSG_INFO_SEARCHING_SHELL_CONFIGS="Searching for shell configurations to remove the PATH entry..."
    MSG_INFO_REMOVING_PATH_ENTRY="Removing yabridge-updater PATH entry from"
    MSG_SUCCESS_PATH_ENTRY_REMOVED="PATH entry removed."
    MSG_SUCCESS_UNINSTALL_COMPLETE="Uninstallation complete!"
    MSG_INFO_RESTART_TERMINAL="You may need to restart your terminal for the PATH changes to take effect."
    MSG_INFO_DOWNLOADING_SCRIPT="Downloading '${SCRIPT_NAME}' from GitHub..."
    MSG_ERR_DOWNLOAD_FAILED="Failed to download '${SCRIPT_NAME}'."
    MSG_ERR_NO_DOWNLOAD_TOOL="Either 'curl' or 'wget' is required for download, but was not found."
fi

remove_path_from_shell_configs() {
    local user_home=$1
    local yabridge_install_dir=$2

    if [ -z "$user_home" ] || [ -z "$yabridge_install_dir" ]; then
        return
    fi

    info "$MSG_INFO_SEARCHING_SHELL_CONFIGS"

    # Array von Shell-Konfigurationsdateien
    local shell_configs=("$user_home/.bashrc" "$user_home/.zshrc" "$user_home/.config/fish/config.fish")
    local marker_comment="# Added by yabridge-updater"
    local found=false

    for config_file in "${shell_configs[@]}"; do
        if [ -f "$config_file" ] && grep -q "$marker_comment" "$config_file"; then
            info "${MSG_INFO_REMOVING_PATH_ENTRY} '$config_file'..."
            # Erstellt eine temporäre Datei ohne den Block und ersetzt dann die Originaldatei
            # Dies ist sicherer als sed -i, da es keine Probleme mit Berechtigungen unter sudo hat
            sed "/${marker_comment}/,+1d" "$config_file" > "${config_file}.tmp"
            # Berechtigungen und Eigentümer von der Originaldatei übernehmen
            chown --reference="$config_file" "${config_file}.tmp"
            chmod --reference="$config_file" "${config_file}.tmp"
            mv "${config_file}.tmp" "$config_file"
            success "$MSG_SUCCESS_PATH_ENTRY_REMOVED"
            found=true
        fi
    done
}

main() {
    info "${MSG_START_UNINSTALL} '$INSTALL_NAME'..."

    # 1. Prüfen, ob das Skript mit Root-Rechten ausgeführt wird
    if [ "$(id -u)" -ne 0 ]; then
        error "$MSG_ERR_NEED_ROOT"
    fi

    # 2. Den ursprünglichen Benutzer ermitteln
    if [ -n "$SUDO_USER" ]; then
        USER_HOME=$(getent passwd "$SUDO_USER" | cut -d: -f6)
    else
        warning "$MSG_WARN_NO_SUDO_USER"
        USER_HOME=""
    fi

    # 3. Das Hauptskript entfernen
    if [ -f "$INSTALL_PATH/$INSTALL_NAME" ]; then
        info "${MSG_INFO_REMOVE_MAIN_SCRIPT} $INSTALL_PATH/$INSTALL_NAME"
        rm -f "$INSTALL_PATH/$INSTALL_NAME"
        success "$MSG_SUCCESS_MAIN_SCRIPT_REMOVED"
    else
        info "$MSG_INFO_MAIN_SCRIPT_NOT_FOUND"
    fi

    # 4. Interaktiv weitere Daten löschen
    if [ -n "$USER_HOME" ]; then
        CONFIG_DIR="$USER_HOME/.config/yabridge-updater"
        PATH_CONFIG_FILE="$CONFIG_DIR/path"

        # Installationspfad ermitteln (benutzerdefiniert oder Standard)
        if [ -f "$PATH_CONFIG_FILE" ] && [ -s "$PATH_CONFIG_FILE" ]; then
            YABRIDGE_INSTALL_DIR=$(cat "$PATH_CONFIG_FILE")
            info "${MSG_INFO_CUSTOM_PATH_FOUND} $YABRIDGE_INSTALL_DIR"
        else
            YABRIDGE_INSTALL_DIR="$USER_HOME/.local/share/yabridge"
        fi

        # Backup-Pfad ableiten
        YABRIDGE_PARENT_DIR=$(dirname "$YABRIDGE_INSTALL_DIR")
        BACKUP_DIR="$YABRIDGE_PARENT_DIR/yabridge-backups"

        echo
        if [ -d "$CONFIG_DIR" ]; then
            prompt_text=$(printf "$MSG_PROMPT_DELETE_CONFIG" "$CONFIG_DIR")
            read -p "$(echo -e "${C_YELLOW}${prompt_text}${C_RESET}")" -r
            if [[ $REPLY =~ ^[JjYy]([Aa][Ss])?$ ]]; then
                info "$MSG_INFO_DELETING_CONFIG"
                rm -rf "$CONFIG_DIR"
                success "$MSG_SUCCESS_CONFIG_DELETED"
            fi
        fi

        if [ -d "$YABRIDGE_INSTALL_DIR" ] || [ -d "$BACKUP_DIR" ]; then
            prompt_text=$(printf "$MSG_PROMPT_DELETE_YABRIDGE_DATA" "$YABRIDGE_INSTALL_DIR" "$BACKUP_DIR")
            read -p "$(echo -e "${C_YELLOW}${prompt_text}${C_RESET}")" -r
            if [[ $REPLY =~ ^[JjYy]([Aa][Ss])?$ ]]; then
                info "$MSG_INFO_DELETING_YABRIDGE_DATA"
                rm -rf "$YABRIDGE_INSTALL_DIR" "$BACKUP_DIR"
                success "$MSG_SUCCESS_YABRIDGE_DATA_DELETED"
            fi
        fi

        # 5. PATH-Eintrag aus Shell-Konfigurationen entfernen
        remove_path_from_shell_configs "$USER_HOME" "$YABRIDGE_INSTALL_DIR"
    fi

    echo
    success "$MSG_SUCCESS_UNINSTALL_COMPLETE"
    info "$MSG_INFO_RESTART_TERMINAL"
}

main