#!/usr/bin/env python3
import argparse
import datetime
import locale
import getpass
import json
import stat
import os
import shutil
import subprocess
import sys
import tarfile
import tempfile
import zipfile
from pathlib import Path

# --- Configuration ---
REPO = "robbert-vdh/yabridge"
# TODO: Trage hier das GitHub-Repository ein, in dem dieses Updater-Skript gehostet wird.
# z.B. "Benutzername/RepoName"
UPDATER_REPO = "mluckau/yabridge_updater"
UPDATER_SOURCE_FILENAME = "yabridge_updater.py"
HOME = Path.home()
CONFIG_DIR = HOME / ".config" / "yabridge-updater"
TOKEN_FILE = CONFIG_DIR / "token"
PATH_CONFIG_FILE = CONFIG_DIR / "path"

# --- Internationalization (i18n) ---
LANG = 'de'  # Default to German
try:
    locale.setlocale(locale.LC_ALL, '')
    lang_code, _ = locale.getlocale()
    if not (lang_code and lang_code.lower().startswith('de')):
        LANG = 'en'
except Exception:
    LANG = 'en'  # Fallback to English if locale detection fails


def get_string(key, **kwargs):
    """Gets a string from the translations dictionary for the current language."""
    # Fallback to English if the key is not in the current language, then to the key itself
    s = TRANSLATIONS.get(key, {}).get(
        LANG, TRANSLATIONS.get(key, {}).get('en', key))
    if kwargs:
        return s.format(**kwargs)
    return s


TRANSLATIONS = {
    # Generic UI
    "error_prefix": {"de": "✗ FEHLER: ", "en": "✗ ERROR: "},
    "warning_prefix": {"de": "WARNUNG: ", "en": "WARNING: "},
    "success_prefix": {"de": "✓ ", "en": "✓ "},
    "info_prefix": {"de": "-> ", "en": "-> "},
    "header_tpl": {"de": "\n== {message} ==\n", "en": "\n== {message} ==\n"},
    "progress_prefix": {"de": "Fortschritt:", "en": "Progress:"},
    "progress_suffix": {"de": "Komplett", "en": "Complete"},

    # Token Management
    "token_loaded_keyring": {"de": "GitHub Token aus dem System-Schlüsselbund geladen.", "en": "Loaded GitHub token from system keyring."},
    "token_keyring_error": {"de": "Fehler beim Zugriff auf den Schlüsselbund mit secret-tool", "en": "Error accessing keyring with secret-tool"},
    "token_secret_tool_error": {"de": "Schwerwiegender Fehler beim Ausführen von `secret-tool`", "en": "Fatal error executing `secret-tool`"},
    "token_openssl_needed": {"de": "'openssl' wird zum Entschlüsseln benötigt, ist aber nicht installiert.", "en": "'openssl' is required for decryption but is not installed."},
    "token_encrypted_found": {"de": "Verschlüsselte Token-Datei gefunden (openssl-Fallback).", "en": "Found encrypted token file (openssl fallback)."},
    "token_decrypt_password_prompt": {"de": "Bitte das Passwort zum Entschlüsseln des Tokens eingeben: ", "en": "Please enter the password to decrypt the token: "},
    "token_decryption_failed": {"de": "Entschlüsselung fehlgeschlagen.", "en": "Decryption failed."},
    "token_keyring_save_success": {"de": "Token wurde sicher im System-Schlüsselbund gespeichert.", "en": "Token securely saved to system keyring."},
    "token_keyring_save_failed": {"de": "Speichern des Tokens im Schlüsselbund fehlgeschlagen.", "en": "Failed to save token to keyring."},
    "token_encrypt_password_prompt": {"de": "Bitte ein Passwort zum Verschlüsseln des Tokens eingeben: ", "en": "Please enter a password to encrypt the token: "},
    "token_password_confirm_prompt": {"de": "Passwort bestätigen: ", "en": "Confirm password: "},
    "token_passwords_mismatch": {"de": "Passwörter stimmen nicht überein. Token wird nicht gespeichert.", "en": "Passwords do not match. Token will not be saved."},
    "token_encrypted_save_success": {"de": "Token wurde verschlüsselt (mit openssl) gespeichert.", "en": "Token saved encrypted (with openssl)."},
    "token_encryption_failed": {"de": "Verschlüsselung mit openssl fehlgeschlagen. Token nicht gespeichert.", "en": "Encryption with openssl failed. Token not saved."},
    "token_auth_required": {"de": "GitHub-API-Authentifizierung ist erforderlich.", "en": "GitHub API authentication is required."},
    "token_pat_prompt": {"de": "Gib dein GitHub PAT ein: ", "en": "Enter your GitHub PAT: "},
    "token_save_prompt": {"de": "Soll das neue Token für die zukünftige Nutzung gespeichert werden? (j/N)", "en": "Save the new token for future use? (y/N)"},
    "token_no_secure_storage": {"de": "Weder 'secret-tool' noch 'openssl' gefunden. Token kann nicht sicher gespeichert werden.", "en": "Neither 'secret-tool' nor 'openssl' found. Cannot save token securely."},
    "token_clearing_header": {"de": "Gespeicherte Tokens löschen", "en": "Clearing Stored Tokens"},
    "token_clearing_keyring": {"de": "Gespeichertes Token im Schlüsselbund gefunden. Versuche zu löschen...", "en": "Found stored token in keyring. Attempting to delete..."},
    "token_clear_keyring_failed": {"de": "Konnte das Token nicht automatisch aus dem Schlüsselbund löschen. Bitte manuell entfernen.", "en": "Could not automatically delete token from keyring. Please remove it manually."},
    "token_clear_keyring_success": {"de": "Token erfolgreich aus dem System-Schlüsselbund entfernt.", "en": "Token successfully removed from system keyring."},
    "token_clear_file_success": {"de": "Verschlüsselte Token-Datei (openssl-Fallback) entfernt.", "en": "Removed encrypted token file (openssl fallback)."},
    "token_clear_finished": {"de": "Token-Löschvorgang abgeschlossen.", "en": "Token clearing process finished."},
    "token_clear_usage_info": {"de": "Verwende 'token --clear' zum Löschen des Tokens.", "en": "Use 'token --clear' to delete the token."},
    "token_none_available": {"de": "Kein GitHub Token verfügbar. Abbruch.", "en": "No GitHub Token available. Aborting."},

    # Branch/Run Logic
    "branch_select_header": {"de": "Branch interaktiv auswählen", "en": "Interactive Branch Selection"},
    "branch_loading": {"de": "Lade verfügbare Branches...", "en": "Loading available branches..."},
    "branch_invalid_list": {"de": "Konnte keine gültige Branch-Liste von GitHub abrufen. Der Token ist möglicherweise ungültig. API-Antwort: {response_text}", "en": "Could not retrieve a valid branch list from GitHub. The token might be invalid. API response: {response_text}"},
    "branch_checking_artifacts": {"de": "Prüfe Branches auf verfügbare Artefakte...", "en": "Checking branches for available artifacts..."},
    "branch_checking_branch": {"de": "  - Prüfe Branch '{name}'...", "en": "  - Checking branch '{name}'..."},
    "branch_no_artifacts_found": {"de": "Keine Branches mit erfolgreichen Builds und Artefakten gefunden.", "en": "No branches with successful builds and artifacts found."},
    "branch_select_prompt_header": {"de": "\nBitte wähle einen Branch aus, von dem installiert werden soll:", "en": "\nPlease select a branch to install from:"},
    "branch_select_prompt": {"de": "Auswahl (1-{count}): ", "en": "Selection (1-{count}): "},
    "branch_you_selected": {"de": "Du hast Branch '{branch}' ausgewählt.", "en": "You selected branch '{branch}'."},
    "run_latest_info": {"de": "Suche nach dem letzten erfolgreichen Workflow-Lauf für Branch '{branch}'...", "en": "Searching for the latest successful workflow run for branch '{branch}'..."},
    "run_no_successful": {"de": "Keine erfolgreichen Workflow-Läufe für diesen Branch gefunden.", "en": "No successful workflow runs found for this branch."},
    "run_no_version_id": {"de": "Konnte die Remote-Versions-ID oder Artefakt-URL nicht ermitteln.", "en": "Could not determine remote version ID or artifact URL."},

    # Installation
    "install_preparing": {"de": "Installation wird vorbereitet", "en": "Preparing Installation"},
    "install_getting_artifacts": {"de": "Rufe Artefakt-Liste ab...", "en": "Fetching artifact list..."},
    "install_no_artifacts_url": {"de": "Konnte nicht beide Artefakt-URLs finden.", "en": "Could not find both artifact URLs."},
    "install_backing_up": {"de": "Sichere bestehende Installation nach {backup_dir}", "en": "Backing up existing installation to {backup_dir}"},
    "install_downloading": {"de": "Lade '{name}' herunter...", "en": "Downloading '{name}'..."},
    "install_not_zip": {"de": "Heruntergeladene Datei für '{name}' ist kein gültiges ZIP-Archiv.", "en": "Downloaded file for '{name}' is not a valid ZIP archive."},
    "install_no_tar": {"de": "Kein .tar.gz-Archiv im '{name}'-Download gefunden.", "en": "No .tar.gz archive found in '{name}' download."},
    "install_update_complete": {"de": "Update auf Version {version} abgeschlossen.", "en": "Update to version {version} completed."},
    "install_path_saved": {"de": "Installationspfad in {path_file} gespeichert.", "en": "Installation path saved in {path_file}."},
    "sync_header": {"de": "Synchronisiere Plugins", "en": "Synchronizing Plugins"},
    "sync_running": {"de": "Führe '{command}' aus...", "en": "Running '{command}'..."},
    "sync_not_found": {"de": "yabridgectl wurde nach der Installation nicht gefunden.", "en": "yabridgectl not found after installation."},

    # PATH Management
    "path_header": {"de": "PATH-Überprüfung", "en": "PATH Check"},
    "path_already_configured": {"de": "Pfad '{path}' ist bereits in '{config_file}' konfiguriert.", "en": "Path '{path}' is already configured in '{config_file}'."},
    "path_needs_adding": {"de": "Der Installationspfad '{path}' muss zu deinem PATH hinzugefügt werden, um 'yabridgectl' direkt aufrufen zu können.", "en": "The installation path '{path}' needs to be added to your PATH to call 'yabridgectl' directly."},
    "path_add_prompt": {"de": "Soll der Pfad automatisch zu '{config_file}' hinzugefügt werden? (j/N)", "en": "Add the path automatically to '{config_file}'? (y/N)"},
    "path_added_success": {"de": "Pfad wurde hinzugefügt. Bitte starte dein Terminal neu oder führe 'source {config_file}' aus, damit die Änderungen wirksam werden.", "en": "Path added. Please restart your terminal or run 'source {config_file}' for the changes to take effect."},
    "path_add_skipped": {"de": "Automatisches Hinzufügen übersprungen. Bitte füge den Pfad manuell hinzu.", "en": "Skipped automatic addition. Please add the path manually."},
    "path_unknown_shell": {"de": "Unbekannte Shell '{shell_name}'. Bitte füge den Pfad '{path}' manuell zu deinem PATH hinzu.", "en": "Unknown shell '{shell_name}'. Please add the path '{path}' to your PATH manually."},

    # Backup / Restore
    "backup_prune_header": {"de": "Alte Backups aufräumen", "en": "Pruning Old Backups"},
    "backup_not_enough": {"de": "Nicht genügend alte Backups zum Aufräumen gefunden.", "en": "Not enough old backups found to prune."},
    "backup_deleting": {"de": "Lösche {count} alte Backup(s)...", "en": "Deleting {count} old backup(s)..."},
    "backup_deleted": {"de": "{name} gelöscht.", "en": "{name} deleted."},
    "backup_delete_failed": {"de": "Konnte Backup {backup_dir} nicht löschen", "en": "Could not delete backup {backup_dir}"},
    "backup_prune_complete": {"de": "Aufräumen der Backups abgeschlossen.", "en": "Backup pruning complete."},
    "restore_header": {"de": "Backup wiederherstellen", "en": "Restore Backup"},
    "restore_no_backups": {"de": "Keine Backups zum Wiederherstellen gefunden.", "en": "No backups found to restore from."},
    "restore_available_header": {"de": "\nVerfügbare Backups (neueste zuerst):", "en": "\nAvailable backups (newest first):"},
    "restore_version_info": {"de": " (Version: {version}, Branch: {branch})", "en": " (Version: {version}, Branch: {branch})"},
    "restore_invalid_version": {"de": " (Ungültige Versionsdatei)", "en": " (Invalid version file)"},
    "restore_prompt": {"de": "Welches Backup wiederherstellen? (1-{count}): ", "en": "Which backup to restore? (1-{count}): "},
    "restore_restoring": {"de": "'{name}' wird wiederhergestellt...", "en": "Restoring '{name}'..."},
    "restore_pre_backup": {"de": "Sichere die aktuelle Installation nach {backup_dir}...", "en": "Backing up the current installation to {backup_dir}..."},
    "restore_with_version_file": {"de": "Installation inklusive .version-Datei wiederhergestellt.", "en": "Restored installation including .version file."},
    "restore_success": {"de": "Wiederherstellung erfolgreich!", "en": "Restore successful!"},
    "restore_failed": {"de": "Wiederherstellung fehlgeschlagen", "en": "Restore failed"},
    "restore_reverting": {"de": "Versuche, die ursprüngliche Installation wiederherzustellen...", "en": "Attempting to restore the original installation..."},
    "restore_process_complete": {"de": "Wiederherstellungsprozess abgeschlossen.", "en": "Restore process completed."},

    # Main Logic / Arguments
    "argparse_description": {"de": "Ein Skript zum Herunterladen und Verwalten von Entwicklerversionen von yabridge.", "en": "A script to download and manage development versions of yabridge."},
    "argparse_install_path_help": {"de": "Benutzerdefinierter Installationspfad für yabridge. Überschreibt gespeicherte Pfade.", "en": "Custom installation path for yabridge. Overwrites saved path."},
    "argparse_commands_title": {"de": "Befehle", "en": "Commands"},
    "argparse_update_help": {"de": "Sucht nach Updates und installiert sie (Standardaktion).", "en": "Checks for updates and installs them (default action)."},
    "argparse_interactive_help": {"de": "Erzwingt die interaktive Auswahl eines Branches.", "en": "Forces interactive branch selection."},
    "argparse_sync_help": {"de": "Führt 'yabridgectl sync' aus, um Plugins zu synchronisieren.", "en": "Runs 'yabridgectl sync' to synchronize plugins."},
    "argparse_status_help": {"de": "Zeigt die aktuell installierte Version und den Pfad an.", "en": "Displays the currently installed version and path."},
    "argparse_restore_help": {"de": "Stellt eine frühere Version aus einem Backup wieder her.", "en": "Restores a previous version from a backup."},
    "argparse_prune_help": {"de": "Löscht alte Backups.", "en": "Deletes old backups."},
    "argparse_keep_help": {"de": "Anzahl der zu behaltenden Backups (Standard: 5).", "en": "Number of backups to keep (default: 5)."},
    "argparse_self_update_help": {"de": "Aktualisiert dieses Skript auf die neueste Version von GitHub.", "en": "Updates this script to the latest version from GitHub."},
    "argparse_token_help": {"de": "Verwaltet den gespeicherten GitHub-Token.", "en": "Manages the stored GitHub token."},
    "argparse_token_clear_help": {"de": "Löscht den gespeicherten GitHub-Token.", "en": "Deletes the stored GitHub token."},
    "path_use_custom": {"de": "Verwende benutzerdefinierten Installationspfad: {path}", "en": "Using custom installation path: {path}"},
    "path_use_saved": {"de": "Verwende gespeicherten Installationspfad: {path}", "en": "Using saved installation path: {path}"},
    "path_use_default": {"de": "Verwende Standard-Installationspfad: {path}", "en": "Using default installation path: {path}"},
    "status_header": {"de": "Status der yabridge-Installation", "en": "Yabridge Installation Status"},
    "status_path": {"de": "  Installationspfad: ", "en": "  Installation path: "},
    "status_yabridgectl_found": {"de": "  yabridgectl gefunden: ", "en": "  yabridgectl found: "},
    "status_yes": {"de": "Ja", "en": "Yes"},
    "status_no": {"de": "Nein (Installation ist beschädigt oder nicht vorhanden)", "en": "No (installation is corrupt or missing)"},
    "status_installed_branch": {"de": "  Installierter Branch: ", "en": "  Installed branch: "},
    "status_installed_version": {"de": "  Installierte Version (SHA): ", "en": "  Installed version (SHA): "},
    "status_version_corrupt": {"de": "Lokale .version-Datei ist korrupt.", "en": "Local .version file is corrupt."},
    "status_unknown_version": {"de": "Unbekannt (keine .version-Datei gefunden)", "en": "Unknown (no .version file found)"},
    "updater_header": {"de": "Yabridge Updater", "en": "Yabridge Updater"},
    "interactive_forced": {"de": "Interaktiver Modus wird erzwungen.", "en": "Forcing interactive mode."},
    "version_file_corrupt_interactive": {"de": "Lokale .version-Datei ist korrupt. Wechsle in den interaktiven Modus.", "en": "Local .version file is corrupt. Switching to interactive mode."},
    "checking_for_updates": {"de": "Prüfe auf Updates für den installierten Branch '{branch}'...", "en": "Checking for updates for installed branch '{branch}'..."},
    "update_available": {"de": "Update von {local_sha} auf {remote_sha} für Branch '{branch}' verfügbar.", "en": "Update from {local_sha} to {remote_sha} available for branch '{branch}'."},
    "install_now_prompt": {"de": "Jetzt installieren? (J/n)", "en": "Install now? (Y/n)"},
    "update_aborted": {"de": "Update abgebrochen.", "en": "Update aborted."},
    "already_latest": {"de": "Du hast bereits die aktuellste Version.", "en": "You already have the latest version."},
    "no_local_version_interactive": {"de": "Keine lokale Version gefunden oder --interactive gesetzt. Starte interaktiven Modus...", "en": "No local version found or --interactive set. Starting interactive mode..."},
    "self_update_header": {"de": "Self-Update", "en": "Self-Update"},
    "self_update_checking": {"de": "Suche nach einer neuen Version des Updaters...", "en": "Checking for a new version of the updater..."},
    "self_update_repo_not_configured": {"de": "Das Repository für das Self-Update ist nicht konfiguriert. Bitte die Variable 'UPDATER_REPO' im Skript anpassen.", "en": "The repository for self-update is not configured. Please edit the 'UPDATER_REPO' variable in the script."},
    "self_update_already_latest": {"de": "Dieses Skript ist bereits auf dem neuesten Stand.", "en": "This script is already up-to-date."},
    "self_update_available": {"de": "Eine neue Version des Updaters ist verfügbar.", "en": "A new version of the updater is available."},
    "self_update_restarting": {"de": "Update erfolgreich. Starte Skript neu...", "en": "Update successful. Restarting script..."},

    # Error Handling
    "error_network": {"de": "Ein Netzwerkfehler bei der Kommunikation mit GitHub ist aufgetreten.", "en": "A network error occurred while communicating with GitHub."},
    "error_subprocess": {"de": "Ein externer Befehl (z.B. yabridgectl) ist fehlgeschlagen.", "en": "An external command (e.g., yabridgectl) failed."},
    "error_file_io": {"de": "Ein Fehler beim Lesen, Schreiben oder Entpacken von Dateien ist aufgetreten.", "en": "An error occurred while reading, writing, or extracting files."},
    "error_internal": {"de": "Ein interner Fehler oder eine unerwartete API-Antwort ist aufgetreten.", "en": "An internal error or an unexpected API response occurred."},
    "error_unexpected": {"de": "Ein unerwarteter, allgemeiner Fehler ist aufgetreten", "en": "An unexpected, general error occurred"},
    "script_finished_success": {"de": "Skript erfolgreich beendet.", "en": "Script finished successfully."},
    "requests_missing": {"de": "Das 'requests' Modul wird benötigt. Bitte installiere es mit z.B. 'pip install requests', 'sudo pacman -S python-requests' oder 'sudo apt install python3-requests'. Je nach Distro kann es verschiedene Installationsmethoden geben. ", "en": "The 'requests' module is required. Please install it, e.g., with 'pip install requests', 'sudo pacman -S python-requests', or 'sudo apt install python3-requests'. Installation methods may vary depending on your distribution. "},
}

# --- UI / Colors ---


class C:
    HEADER = '\033[95m'
    OKBLUE = '\033[94m'
    OKCYAN = '\033[96m'
    OKGREEN = '\033[92m'
    WARNING = '\033[93m'
    FAIL = '\033[91m'
    ENDC = '\033[0m'
    BOLD = '\033[1m'
    UNDERLINE = '\033[4m'


# --- Global State ---
_rate_limit_warning_shown = False

# --- Helper Functions ---


def print_error(message, details=""):
    """Prints an error message to stderr."""
    print(f"{C.FAIL}{get_string('error_prefix')}{message}{C.ENDC}", file=sys.stderr)
    if details:
        print(f"{C.FAIL}    {details}{C.ENDC}", file=sys.stderr)


def print_warning(message):
    """Prints a warning message to stderr."""
    print(f"{C.WARNING}{get_string('warning_prefix')}{message}{C.ENDC}",
          file=sys.stderr)


def print_success(message):
    """Prints a success message."""
    print(f"{C.OKGREEN}{get_string('success_prefix')}{message}{C.ENDC}")


def print_info(message):
    """Prints an informational message."""
    print(f"{C.BOLD}{get_string('info_prefix')}{C.ENDC}{message}")


def print_header(message):
    """Prints a header message."""
    print(f"{C.HEADER}{get_string('header_tpl', message=message)}{C.ENDC}")


def print_progress_bar(iteration, total, prefix='', suffix='', decimals=1, length=50, fill='█'):
    """Call in a loop to create terminal progress bar."""
    if total == 0:
        total = 1
    percent = ("{0:." + str(decimals) + "f}").format(100 *
                                                     (iteration / float(total)))
    filled_length = int(length * iteration // total)
    bar = fill * filled_length + '-' * (length - filled_length)
    sys.stdout.write(f'\r{prefix} |{bar}| {percent}% {suffix}')
    sys.stdout.flush()


def check_command_exists(cmd):
    """Checks if a command exists on the system."""
    return shutil.which(cmd) is not None


def check_rate_limit(response):
    """Checks GitHub API rate limit and prints a warning if it's low."""
    global _rate_limit_warning_shown
    if _rate_limit_warning_shown:
        return
    if 'X-RateLimit-Remaining' in response.headers:
        remaining = int(response.headers['X-RateLimit-Remaining'])
        if remaining < 100:
            reset_time_unix = int(response.headers['X-RateLimit-Reset'])
            reset_datetime = datetime.datetime.fromtimestamp(reset_time_unix)
            # This string is not translated as it's a developer-facing debug message
            print_warning(
                f"Only {remaining} GitHub API requests left. Limit resets at: {reset_datetime.strftime('%Y-%m-%d %H:%M:%S')}")
            _rate_limit_warning_shown = True

# --- Token Management ---


def get_github_token_from_keyring():
    if not check_command_exists("secret-tool"):
        return None
    try:
        result = subprocess.run(["secret-tool", "lookup", "service",
                                "yabridge-updater"], capture_output=True, text=True, check=False)
        if result.returncode == 0 and result.stdout.strip():
            print_info(get_string("token_loaded_keyring"))
            return result.stdout.strip()
        elif result.returncode != 0:
            stderr_msg = result.stderr.strip()
            if "No such secret" not in stderr_msg and stderr_msg:
                print_error(get_string("token_keyring_error"),
                            details=f"(Code: {result.returncode}): {stderr_msg}")
    except (subprocess.SubprocessError, FileNotFoundError) as e:
        print_error(get_string("token_secret_tool_error"), details=e)
    return None


def get_github_token_from_file():
    if not TOKEN_FILE.exists():
        return None
    if not check_command_exists("openssl"):
        print_error(get_string("token_openssl_needed"))
        return None
    print_info(get_string("token_encrypted_found"))
    password = getpass.getpass(get_string("token_decrypt_password_prompt"))
    try:
        process = subprocess.run(["openssl", "enc", "-aes-256-cbc", "-a", "-d", "-salt", "-pbkdf2", "-pass",
                                 f"pass:{password}"], input=TOKEN_FILE.read_text(), capture_output=True, text=True, check=True)
        decrypted_token = process.stdout.strip()
        if not decrypted_token:
            print_error(get_string("token_decryption_failed"))
        return decrypted_token
    except (subprocess.SubprocessError, FileNotFoundError) as e:
        print_error(get_string("token_decryption_failed"), details=e)
    return None


def save_token_to_keyring(token):
    try:
        subprocess.run(["secret-tool", "store", "--label=yabridge-updater GitHub PAT", "service",
                       "yabridge-updater"], input=token, text=True, check=True, capture_output=True)
        print_success(get_string("token_keyring_save_success"))
    except (subprocess.SubprocessError, FileNotFoundError):
        print_error(get_string("token_keyring_save_failed"))


def save_token_to_file(token):
    password = getpass.getpass(get_string("token_encrypt_password_prompt"))
    if password != getpass.getpass(get_string("token_password_confirm_prompt")):
        print_error(get_string("token_passwords_mismatch"))
        return
    try:
        process = subprocess.run(["openssl", "enc", "-aes-256-cbc", "-a", "-salt", "-pbkdf2",
                                 "-pass", f"pass:{password}"], input=token, capture_output=True, text=True, check=True)
        CONFIG_DIR.mkdir(exist_ok=True)
        TOKEN_FILE.write_text(process.stdout)
        TOKEN_FILE.chmod(0o600)
        print_success(get_string("token_encrypted_save_success"))
    except (subprocess.SubprocessError, FileNotFoundError):
        print_error(get_string("token_encryption_failed"))


def get_token():
    token = os.environ.get("GITHUB_TOKEN")
    if token:
        return token, "env"
    token = get_github_token_from_keyring()
    if token:
        return token, "keyring"
    token = get_github_token_from_file()
    if token:
        return token, "file"

    print_info(get_string("token_auth_required"))
    token = getpass.getpass(get_string("token_pat_prompt"))
    if not token:
        return None, None

    if input(f"{C.WARNING}{get_string('token_save_prompt')}{C.ENDC} ").lower().strip() in ["j", "ja", "y", "yes"]:
        if check_command_exists("secret-tool"):
            save_token_to_keyring(token)
        elif check_command_exists("openssl"):
            save_token_to_file(token)
        else:
            print_error(get_string("token_no_secure_storage"))
    return token, "prompt"


def clear_tokens():
    print_header(get_string("token_clearing_header"))
    if check_command_exists("secret-tool") and subprocess.run(["secret-tool", "lookup", "service", "yabridge-updater"], capture_output=True).returncode == 0:
        print_info(get_string("token_clearing_keyring"))
        subprocess.run(["secret-tool", "clear", "service",
                       "yabridge-updater"], check=False)
        if subprocess.run(["secret-tool", "lookup", "service", "yabridge-updater"], capture_output=True).returncode == 0:
            print_error(get_string("token_clear_keyring_failed"))
        else:
            print_success(get_string("token_clear_keyring_success"))
    if TOKEN_FILE.exists():
        TOKEN_FILE.unlink()
        print_success(get_string("token_clear_file_success"))
    print_info(get_string("token_clear_finished"))

# --- Core Logic Functions ---


def select_branch(headers, token_source):
    print_header(get_string("branch_select_header"))
    print_info(get_string("branch_loading"))
    response = requests.get(
        f"https://api.github.com/repos/{REPO}/branches", headers=headers)
    check_rate_limit(response)
    response.raise_for_status()
    branches_json = response.json()

    if not isinstance(branches_json, list) or not branches_json:
        raise ValueError(get_string("branch_invalid_list",
                         response_text=response.text))

    print_info(get_string("branch_checking_artifacts"))
    branches_with_artifacts = []
    for name in [branch["name"] for branch in branches_json]:
        print(get_string("branch_checking_branch", name=name))
        url = f"https://api.github.com/repos/{REPO}/actions/runs?branch={name}&status=success&per_page=1"
        run_response = requests.get(url, headers=headers)
        check_rate_limit(run_response)
        if run_response.status_code == 200 and run_response.json().get("workflow_runs"):
            branches_with_artifacts.append(name)

    if not branches_with_artifacts:
        raise ValueError(get_string("branch_no_artifacts_found"))

    print(f"\n{C.BOLD}{get_string('branch_select_prompt_header')}{C.ENDC}")
    for i, name in enumerate(branches_with_artifacts, 1):
        print(f"  {C.OKCYAN}{i}){C.ENDC} {name}")

    choice = -1
    while not (1 <= choice <= len(branches_with_artifacts)):
        try:
            choice = int(input(get_string("branch_select_prompt",
                         count=len(branches_with_artifacts))))
        except ValueError:
            pass

    branch = branches_with_artifacts[choice - 1]
    print_info(get_string("branch_you_selected",
               branch=f"{C.OKCYAN}{branch}{C.ENDC}"))
    return branch


def get_latest_run_info(branch, headers):
    print_info(get_string("run_latest_info",
               branch=f"{C.OKCYAN}{branch}{C.ENDC}"))
    url = f"https://api.github.com/repos/{REPO}/actions/runs?branch={branch}&status=success&per_page=1"
    response = requests.get(url, headers=headers)
    check_rate_limit(response)
    response.raise_for_status()
    runs_json = response.json()

    if not runs_json.get("workflow_runs"):
        raise ValueError(get_string("run_no_successful"))
    latest_run = runs_json["workflow_runs"][0]
    remote_version, artifacts_url = latest_run["head_sha"], latest_run["artifacts_url"]
    if not remote_version or not artifacts_url:
        raise ValueError(get_string("run_no_version_id"))
    return remote_version, artifacts_url


def download_and_extract(name, url, headers, tmp_path, yabridge_dir):
    print_info(get_string("install_downloading",
               name=f"{C.OKCYAN}{name}{C.ENDC}"))
    dl_response = requests.get(
        url, headers=headers, allow_redirects=True, stream=True)
    check_rate_limit(dl_response)
    dl_response.raise_for_status()
    total_size = int(dl_response.headers.get('content-length', 0))
    zip_path = tmp_path / f"{name}.zip"

    with open(zip_path, 'wb') as f:
        if total_size > 0:
            print_progress_bar(0, total_size, prefix=f"{C.OKGREEN}{get_string('progress_prefix')}{C.ENDC}", suffix=get_string(
                'progress_suffix'), length=40)
        downloaded_size = 0
        for chunk in dl_response.iter_content(chunk_size=8192):
            f.write(chunk)
            downloaded_size += len(chunk)
            if total_size > 0:
                print_progress_bar(downloaded_size, total_size, prefix=f"{C.OKGREEN}{get_string('progress_prefix')}{C.ENDC}", suffix=get_string(
                    'progress_suffix'), length=40)
    sys.stdout.write('\n')
    sys.stdout.flush()

    if not zipfile.is_zipfile(zip_path):
        raise IOError(get_string("install_not_zip", name=name))
    with zipfile.ZipFile(zip_path, 'r') as zip_ref:
        zip_ref.extractall(tmp_path / f"{name}_ext")
    tar_path = next((tmp_path / f"{name}_ext").glob('*.tar.gz'), None)
    if not tar_path:
        raise IOError(get_string("install_no_tar", name=name))

    with tarfile.open(tar_path, "r:gz") as tar:
        def strip_filter(member, path):
            try:
                new_parts = Path(member.name).parts[1:]
                if not new_parts:
                    return None
                member.name = str(Path(*new_parts))
            except IndexError:
                return None
            return member
        if sys.version_info >= (3, 12):
            tar.extractall(path=yabridge_dir, filter=strip_filter)
        else:
            members = [m for m in [strip_filter(
                m, '') for m in tar.getmembers()] if m is not None]
            tar.extractall(path=yabridge_dir, members=members)


def perform_installation(artifacts_url, headers, yabridge_dir, remote_version, branch_name):
    with tempfile.TemporaryDirectory() as tmpdir:
        tmp_path = Path(tmpdir)
        print_header(get_string("install_preparing"))
        print_info(get_string("install_getting_artifacts"))
        response = requests.get(artifacts_url, headers=headers)
        check_rate_limit(response)
        response.raise_for_status()
        artifacts = response.json()["artifacts"]

        ctl_artifact = next(
            (a for a in artifacts if a["name"].startswith("yabridgectl")), None)
        libs_artifact = next(
            (a for a in artifacts if a["name"].startswith("yabridge-")), None)
        if not ctl_artifact or not libs_artifact:
            raise ValueError(get_string("install_no_artifacts_url"))

        backup_base_dir = yabridge_dir.parent / "yabridge-backups"
        if yabridge_dir.exists():
            backup_base_dir.mkdir(exist_ok=True)
            backup_dir = backup_base_dir / \
                f"yabridge-backup-{datetime.datetime.now().strftime('%F-%H%M%S')}"
            print_info(get_string("install_backing_up",
                       backup_dir=f"{C.OKCYAN}{backup_dir}{C.ENDC}"))
            shutil.move(str(yabridge_dir), str(backup_dir))
        yabridge_dir.mkdir(parents=True, exist_ok=True)

        download_and_extract(
            "ctl", ctl_artifact["archive_download_url"], headers, tmp_path, yabridge_dir)
        download_and_extract(
            "libs", libs_artifact["archive_download_url"], headers, tmp_path, yabridge_dir)

        CONFIG_DIR.mkdir(exist_ok=True)
        version_data = {"sha": remote_version, "branch": branch_name}
        (yabridge_dir / ".version").write_text(json.dumps(version_data, indent=4))
        PATH_CONFIG_FILE.write_text(str(yabridge_dir))
        print_success(get_string("install_update_complete",
                      version=f"{C.BOLD}{remote_version[:7]}{C.ENDC}"))
        print_info(get_string("install_path_saved",
                   path_file=f"{C.OKCYAN}{PATH_CONFIG_FILE}{C.ENDC}"))


def run_sync(yabridgectl_path):
    print_header(get_string("sync_header"))
    command_str = f"{yabridgectl_path} sync --prune"
    print_info(get_string("sync_running",
               command=f"{C.OKCYAN}{command_str}{C.ENDC}"))
    if not yabridgectl_path.exists():
        raise FileNotFoundError(get_string("sync_not_found"))
    subprocess.run([str(yabridgectl_path), "sync", "--prune"], check=True)


def check_and_update_path(yabridge_dir):
    print_header(get_string("path_header"))
    install_path_str = str(yabridge_dir)
    # We check the raw PATH environment variable, as the script might be run with sudo
    # which can have a different PATH than the user's interactive shell.

    shell_name = Path(os.environ.get("SHELL", "")).name
    config_file, line_to_add = None, None

    if shell_name == "bash":
        config_file, line_to_add = HOME / \
            ".bashrc", f'export PATH="{install_path_str}:$PATH"'
    elif shell_name == "zsh":
        config_file, line_to_add = HOME / \
            ".zshrc", f'export PATH="{install_path_str}:$PATH"'
    elif shell_name == "fish":
        config_file, line_to_add = HOME / ".config" / "fish" / \
            "config.fish", f"fish_add_path {install_path_str}"

    if config_file and line_to_add:
        # Check if the line is already in the file to avoid duplicates
        if config_file.exists() and line_to_add in config_file.read_text():
            print_info(get_string("path_already_configured",
                       path=install_path_str, config_file=config_file))
            return

        print_warning(get_string("path_needs_adding", path=install_path_str))
        prompt = f"{C.WARNING}{get_string('path_add_prompt', config_file=config_file)}{C.ENDC} "
        if input(prompt).lower().strip() in ["j", "ja", "y", "yes"]:
            with config_file.open("a") as f:
                f.write(f"\n# Added by yabridge-updater\n{line_to_add}\n")
            print_success(get_string(
                "path_added_success", config_file=config_file))
        else:
            print_info(get_string("path_add_skipped"))
    else:
        print_warning(get_string("path_unknown_shell",
                      shell_name=shell_name, path=install_path_str))


def prune_backups(backup_parent_dir, keep_count):
    backup_base_dir = backup_parent_dir / "yabridge-backups"
    print_header(get_string("backup_prune_header"))
    backups = sorted([d for d in backup_base_dir.glob("yabridge-backup-*")
                     if d.is_dir()], key=lambda d: d.name, reverse=True)

    if len(backups) <= keep_count:
        print_info(get_string("backup_not_enough"))
        return

    to_delete = backups[keep_count:]
    print_info(get_string("backup_deleting", count=len(to_delete)))
    for backup_dir in to_delete:
        try:
            shutil.rmtree(backup_dir)
            print(
                f"  - {C.OKCYAN}{get_string('backup_deleted', name=backup_dir.name)}{C.ENDC}")
        except OSError as e:
            print_error(get_string("backup_delete_failed",
                        backup_dir=backup_dir), details=e)
    print_success(get_string("backup_prune_complete"))


def restore_from_backup(yabridge_dir):
    print_header(get_string("restore_header"))
    backup_base_dir = yabridge_dir.parent / "yabridge-backups"
    backups = sorted([d for d in backup_base_dir.glob("yabridge-backup-*")
                     if d.is_dir()], key=lambda d: d.name, reverse=True)

    if not backups:
        raise FileNotFoundError(get_string("restore_no_backups"))

    print(f"\n{C.BOLD}{get_string('restore_available_header')}{C.ENDC}")
    for i, backup in enumerate(backups, 1):
        version_str = ""
        version_file_in_backup = backup / ".version"
        if version_file_in_backup.is_file():
            try:
                version_data = json.loads(version_file_in_backup.read_text())
                version_sha, version_branch = version_data.get(
                    "sha", "N/A")[:7], version_data.get("branch", "N/A")
                version_str = get_string(
                    "restore_version_info", version=f"{C.OKGREEN}{version_sha}{C.ENDC}", branch=f"{C.OKCYAN}{version_branch}{C.ENDC}")
            except json.JSONDecodeError:
                version_str = f" {C.FAIL}{get_string('restore_invalid_version')}{C.ENDC}"
        date_str = backup.name.replace("yabridge-backup-", "")
        print(f"  {C.OKCYAN}{i}){C.ENDC} {date_str}{version_str}")

    choice = -1
    while not (1 <= choice <= len(backups)):
        try:
            choice = int(
                input(get_string("restore_prompt", count=len(backups))))
        except ValueError:
            pass

    selected_backup = backups[choice - 1]
    print_info(get_string("restore_restoring",
               name=f"{C.OKCYAN}{selected_backup.name}{C.ENDC}"))

    backup_base_dir.mkdir(exist_ok=True)
    if yabridge_dir.exists():
        pre_restore_backup_dir = backup_base_dir / \
            f"yabridge-pre-restore-backup-{datetime.datetime.now().strftime('%F-%H%M%S')}"
        print_info(get_string("restore_pre_backup",
                   backup_dir=f"{C.OKCYAN}{pre_restore_backup_dir}{C.ENDC}"))
        shutil.move(str(yabridge_dir), str(pre_restore_backup_dir))

    try:
        shutil.move(str(selected_backup), str(yabridge_dir))
        if (yabridge_dir / ".version").is_file():
            print_info(get_string("restore_with_version_file"))
        print_success(get_string("restore_success"))
    except OSError as e:
        print_error(get_string("restore_failed"), details=e)
        if 'pre_restore_backup_dir' in locals() and pre_restore_backup_dir.exists():
            print_info(get_string("restore_reverting"))
            # No need to call check_and_update_path here, as the path hasn't changed.
            shutil.move(str(pre_restore_backup_dir), str(yabridge_dir))
        sys.exit(1)


def perform_self_update(headers):
    """Checks for a new version of this script and updates it."""
    print_header(get_string("self_update_header"))

    if not UPDATER_REPO or "Benutzername/RepoName" in UPDATER_REPO:
        print_error(get_string("self_update_repo_not_configured"))
        sys.exit(1)

    print_info(get_string("self_update_checking"))
    url = f"https://raw.githubusercontent.com/{UPDATER_REPO}/main/{UPDATER_SOURCE_FILENAME}"
    response = requests.get(url, headers=headers)
    response.raise_for_status()
    latest_content = response.text

    current_script_path = Path(__file__).resolve()
    current_content = current_script_path.read_text()

    # Compare content without the shebang line to avoid updates just for shebang changes
    current_content_body = '\n'.join(current_content.splitlines()[1:])
    latest_content_body = '\n'.join(latest_content.splitlines()[1:])

    if latest_content_body == current_content_body:
        print_success(get_string("self_update_already_latest"))
        return

    print_info(get_string("self_update_available"))
    if input(f"{C.WARNING}{get_string('install_now_prompt')}{C.ENDC} ").lower().strip() in ["", "j", "ja", "y", "yes"]:
        # Preserve the shebang from the currently installed script
        current_shebang = current_content.splitlines()[0]
        if current_shebang.startswith("#!"):
            latest_lines = latest_content.splitlines()
            latest_lines[0] = current_shebang
            latest_content = '\n'.join(latest_lines) + '\n'

        new_script_path = current_script_path.with_suffix('.py.new')
        new_script_path.write_text(latest_content)

        # Copy permissions from old script to new script
        current_mode = stat.S_IMODE(os.stat(current_script_path).st_mode)
        os.chmod(new_script_path, current_mode)

        os.rename(new_script_path, current_script_path)
        print_success(get_string("self_update_restarting"))
        os.execv(sys.executable, [sys.executable] + sys.argv)
    else:
        print_info(get_string("update_aborted"))


def handle_arguments():
    parser = argparse.ArgumentParser(
        description=get_string("argparse_description"), formatter_class=argparse.RawTextHelpFormatter)
    parser.add_argument("--install-path", type=Path, default=None,
                        help=get_string("argparse_install_path_help"))
    subparsers = parser.add_subparsers(
        dest="command", title=get_string("argparse_commands_title"))

    update_parser = subparsers.add_parser(
        "update", help=get_string("argparse_update_help"))
    update_parser.add_argument("--interactive", action="store_true",
                               help=get_string("argparse_interactive_help"))
    subparsers.add_parser(
        "sync", help=get_string("argparse_sync_help"))
    subparsers.add_parser(
        "status", help=get_string("argparse_status_help"))
    subparsers.add_parser(
        "restore", help=get_string("argparse_restore_help"))
    prune_parser = subparsers.add_parser(
        "prune-backups", help=get_string("argparse_prune_help"))
    prune_parser.add_argument("keep", type=int, nargs="?", default=5,
                              help=get_string("argparse_keep_help"))
    token_parser = subparsers.add_parser(
        "token", help=get_string("argparse_token_help"))
    subparsers.add_parser(
        "self-update", help=get_string("argparse_self_update_help"))
    token_parser.add_argument(
        "--clear", action="store_true", help=get_string("argparse_token_clear_help"))
    return parser.parse_args()


def determine_install_path(args):
    if args.install_path:
        yabridge_dir = args.install_path.resolve()
        print_info(get_string("path_use_custom",
                   path=f"{C.OKCYAN}{args.install_path}{C.ENDC}"))
    elif PATH_CONFIG_FILE.exists() and PATH_CONFIG_FILE.read_text().strip():
        yabridge_dir = Path(PATH_CONFIG_FILE.read_text().strip()).resolve()
        print_info(get_string("path_use_saved",
                   path=f"{C.OKCYAN}{yabridge_dir}{C.ENDC}"))
    else:
        yabridge_dir = HOME / ".local" / "share" / "yabridge"
        print_info(get_string("path_use_default",
                   path=f"{C.OKCYAN}{yabridge_dir}{C.ENDC}"))
    return yabridge_dir, yabridge_dir / "yabridgectl"

# --- Main Execution ---


def main():
    """Main script logic."""
    args = handle_arguments()
    command = args.command if args.command else 'update'
    yabridge_dir, yabridgectl_path = determine_install_path(args)

    try:
        if command == 'status':
            print_header(get_string("status_header"))
            print(f"{get_string('status_path')}{C.OKCYAN}{yabridge_dir}{C.ENDC}")
            if yabridgectl_path.exists():
                print(
                    f"{get_string('status_yabridgectl_found')}{C.OKGREEN}{get_string('status_yes')}{C.ENDC}")
            else:
                print(
                    f"{get_string('status_yabridgectl_found')}{C.FAIL}{get_string('status_no')}{C.ENDC}")
            version_file_in_install = yabridge_dir / ".version"
            if version_file_in_install.is_file():
                try:
                    version_data = json.loads(
                        version_file_in_install.read_text())
                    print(
                        f"{get_string('status_installed_branch')}{C.OKCYAN}{version_data.get('branch', 'N/A')}{C.ENDC}")
                    print(
                        f"{get_string('status_installed_version')}{C.OKGREEN}{version_data.get('sha', 'N/A')}{C.ENDC}")
                except json.JSONDecodeError:
                    print_error(get_string("status_version_corrupt"))
            else:
                print(
                    f"{get_string('status_installed_version')}{C.WARNING}{get_string('status_unknown_version')}{C.ENDC}")
            sys.exit(0)

        if command == 'sync':
            run_sync(yabridgectl_path)
            sys.exit(0)

        if command == 'restore':
            restore_from_backup(yabridge_dir)
            run_sync(yabridgectl_path)
            check_and_update_path(yabridge_dir)  # Check path after restore
            print_success(get_string("restore_process_complete"))
            sys.exit(0)

        if command == 'prune-backups':
            prune_backups(yabridge_dir.parent, args.keep)
            sys.exit(0)

        if command == 'token':
            if args.clear:
                clear_tokens()
            else:
                print_info(get_string("token_clear_usage_info"))
            sys.exit(0)

        # Self-update must be handled before other commands that need a token
        if command == 'self-update':
            token, _ = get_token()
            if not token:
                raise ValueError(get_string("token_none_available"))
            headers = {"Authorization": f"Bearer {token}"}
            perform_self_update(headers)
            sys.exit(0)

        if command == 'update':
            print_header(get_string("updater_header"))
            token, token_source = get_token()
            if not token:
                raise ValueError(get_string("token_none_available"))
            headers = {"Authorization": f"Bearer {token}",
                       "Accept": "application/vnd.github.v3+json"}

            version_file_in_install = yabridge_dir / ".version"
            local_info, is_interactive = None, getattr(
                args, 'interactive', False)

            if is_interactive:
                print_info(get_string("interactive_forced"))
            elif version_file_in_install.is_file():
                try:
                    local_info = json.loads(
                        version_file_in_install.read_text())
                except json.JSONDecodeError:
                    print_warning(get_string(
                        "version_file_corrupt_interactive"))
                    is_interactive = True

            if not is_interactive and local_info and local_info.get("branch") and local_info.get("sha"):
                local_branch, local_sha = local_info["branch"], local_info["sha"]
                print_info(get_string("checking_for_updates",
                           branch=f"{C.OKCYAN}{local_branch}{C.ENDC}"))
                remote_sha, artifacts_url = get_latest_run_info(
                    local_branch, headers)

                if remote_sha != local_sha:
                    print_info(get_string(
                        "update_available", local_sha=f"{C.WARNING}{local_sha[:7]}{C.ENDC}", remote_sha=f"{C.OKGREEN}{remote_sha[:7]}{C.ENDC}", branch=local_branch))
                    if input(f"{C.WARNING}{get_string('install_now_prompt')}{C.ENDC} ").lower().strip() in ["", "j", "ja", "y", "yes"]:
                        perform_installation(
                            artifacts_url, headers, yabridge_dir, remote_sha, local_branch)
                        check_and_update_path(yabridge_dir)
                        run_sync(yabridgectl_path)
                    else:
                        print_info(get_string("update_aborted"))
                else:
                    print_success(get_string("already_latest"))
            else:
                print_info(get_string("no_local_version_interactive"))
                branch = select_branch(headers, token_source)
                remote_version, artifacts_url = get_latest_run_info(
                    branch, headers)
                perform_installation(artifacts_url, headers,
                                     yabridge_dir, remote_version, branch)
                check_and_update_path(yabridge_dir)
                run_sync(yabridgectl_path)

    except requests.RequestException as e:
        print_error(get_string("error_network"), details=e)
    except subprocess.SubprocessError as e:
        print_error(get_string("error_subprocess"), details=e)
    except (IOError, zipfile.BadZipFile, tarfile.TarError) as e:
        print_error(get_string("error_file_io"), details=e)
    except (FileNotFoundError, ValueError) as e:
        print_error(get_string("error_internal"), details=e)
    except Exception as e:
        print_error(get_string("error_unexpected"), details=e)
        sys.exit(1)

    print_success(get_string("script_finished_success"))


if __name__ == "__main__":
    try:
        import requests
    except ImportError:
        # This message cannot be translated as the translation engine is not yet available.
        # It's kept simple and includes multi-language install hints.
        print_error("The 'requests' module is required. Please install it, e.g., with 'pip install requests', 'sudo pacman -S python-requests', or 'sudo apt install python3-requests'.")
        sys.exit(1)
    main()
