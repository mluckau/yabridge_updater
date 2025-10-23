#!/usr/bin/env python3
import argparse
import datetime
import getpass
import json
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
HOME = Path.home()
CONFIG_DIR = HOME / ".config" / "yabridge-updater"
TOKEN_FILE = CONFIG_DIR / "token"
PATH_CONFIG_FILE = CONFIG_DIR / "path"

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
    print(f"{C.FAIL}✗ FEHLER: {message}{C.ENDC}", file=sys.stderr)
    if details:
        print(f"{C.FAIL}    Details: {details}{C.ENDC}", file=sys.stderr)


def print_warning(message):
    """Prints a warning message to stderr."""
    print(f"{C.WARNING}WARNUNG: {message}{C.ENDC}", file=sys.stderr)


def print_success(message):
    """Prints a success message."""
    print(f"{C.OKGREEN}✓ {message}{C.ENDC}")


def print_info(message):
    """Prints an informational message."""
    print(f"{C.BOLD}->{C.ENDC} {message}")


def print_header(message):
    """Prints a header message."""
    print(f"\n{C.HEADER}== {message} =={C.ENDC}")


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
            print_warning(f"Nur noch {remaining} GitHub API-Anfragen übrig.")
            print_warning(
                f"  Das Limit wird zurückgesetzt um: {reset_datetime.strftime('%Y-%m-%d %H:%M:%S')}")
            _rate_limit_warning_shown = True

# --- Token Management ---


def get_github_token_from_keyring():
    if not check_command_exists("secret-tool"):
        return None
    try:
        result = subprocess.run(["secret-tool", "lookup", "service",
                                "yabridge-updater"], capture_output=True, text=True, check=False)
        if result.returncode == 0 and result.stdout.strip():
            print_info("GitHub Token aus dem System-Schlüsselbund geladen.")
            return result.stdout.strip()
        elif result.returncode != 0:
            stderr_msg = result.stderr.strip()
            if "No such secret" not in stderr_msg and stderr_msg:
                print_error("Fehler beim Zugriff auf den Schlüsselbund mit secret-tool",
                            details=f"(Code: {result.returncode}): {stderr_msg}")
    except (subprocess.SubprocessError, FileNotFoundError) as e:
        print_error(
            "Schwerwiegender Fehler beim Ausführen von `secret-tool`", details=e)
    return None


def get_github_token_from_file():
    if not TOKEN_FILE.exists():
        return None
    if not check_command_exists("openssl"):
        print_error(
            "'openssl' wird zum Entschlüsseln benötigt, ist aber nicht installiert.")
        return None
    print_info("Verschlüsselte Token-Datei gefunden (openssl-Fallback).")
    password = getpass.getpass(
        "Bitte das Passwort zum Entschlüsseln des Tokens eingeben: ")
    try:
        process = subprocess.run(["openssl", "enc", "-aes-256-cbc", "-a", "-d", "-salt", "-pbkdf2", "-pass",
                                 f"pass:{password}"], input=TOKEN_FILE.read_text(), capture_output=True, text=True, check=True)
        decrypted_token = process.stdout.strip()
        if not decrypted_token:
            print_error("Entschlüsselung fehlgeschlagen.")
        return decrypted_token
    except (subprocess.SubprocessError, FileNotFoundError) as e:
        print_error("Entschlüsselung fehlgeschlagen", details=e)
    return None


def save_token_to_keyring(token):
    try:
        subprocess.run(["secret-tool", "store", "--label=yabridge-updater GitHub PAT", "service",
                       "yabridge-updater"], input=token, text=True, check=True, capture_output=True)
        print_success(
            "Token wurde sicher im System-Schlüsselbund gespeichert.")
    except (subprocess.SubprocessError, FileNotFoundError):
        print_error("Speichern des Tokens im Schlüsselbund fehlgeschlagen.")


def save_token_to_file(token):
    password = getpass.getpass(
        "Bitte ein Passwort zum Verschlüsseln des Tokens eingeben: ")
    if password != getpass.getpass("Passwort bestätigen: "):
        print_error(
            "Passwörter stimmen nicht überein. Token wird nicht gespeichert.")
        return
    try:
        process = subprocess.run(["openssl", "enc", "-aes-256-cbc", "-a", "-salt", "-pbkdf2",
                                 "-pass", f"pass:{password}"], input=token, capture_output=True, text=True, check=True)
        CONFIG_DIR.mkdir(exist_ok=True)
        TOKEN_FILE.write_text(process.stdout)
        TOKEN_FILE.chmod(0o600)
        print_success("Token wurde verschlüsselt (mit openssl) gespeichert.")
    except (subprocess.SubprocessError, FileNotFoundError):
        print_error(
            "Verschlüsselung mit openssl fehlgeschlagen. Token nicht gespeichert.")


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

    print_info("GitHub-API-Authentifizierung ist erforderlich.")
    token = getpass.getpass("Gib dein GitHub PAT ein: ")
    if not token:
        return None, None

    if input(f"{C.WARNING}Soll das neue Token für die zukünftige Nutzung gespeichert werden? (j/N){C.ENDC} ").lower() in ["j", "ja"]:
        if check_command_exists("secret-tool"):
            save_token_to_keyring(token)
        elif check_command_exists("openssl"):
            save_token_to_file(token)
        else:
            print_error(
                "Weder 'secret-tool' noch 'openssl' gefunden. Token kann nicht sicher gespeichert werden.")
    return token, "prompt"


def clear_tokens():
    print_header("Gespeicherte Tokens löschen")
    if check_command_exists("secret-tool") and subprocess.run(["secret-tool", "lookup", "service", "yabridge-updater"], capture_output=True).returncode == 0:
        print_info(
            "Gespeichertes Token im Schlüsselbund gefunden. Versuche zu löschen...")
        subprocess.run(["secret-tool", "clear", "service",
                       "yabridge-updater"], check=False)
        if subprocess.run(["secret-tool", "lookup", "service", "yabridge-updater"], capture_output=True).returncode == 0:
            print_error(
                "Konnte das Token nicht automatisch aus dem Schlüsselbund löschen. Bitte manuell entfernen.")
        else:
            print_success(
                "Token erfolgreich aus dem System-Schlüsselbund entfernt.")
    if TOKEN_FILE.exists():
        TOKEN_FILE.unlink()
        print_success(
            "Verschlüsselte Token-Datei (openssl-Fallback) entfernt.")
    print_info("Token-Löschvorgang abgeschlossen.")

# --- Core Logic Functions ---


def select_branch(headers, token_source):
    print_header("Branch interaktiv auswählen")
    print_info("Lade verfügbare Branches...")
    response = requests.get(
        f"https://api.github.com/repos/{REPO}/branches", headers=headers)
    check_rate_limit(response)
    response.raise_for_status()
    branches_json = response.json()

    if not isinstance(branches_json, list) or not branches_json:
        raise ValueError(
            f"Konnte keine gültige Branch-Liste von GitHub abrufen. Der Token ist möglicherweise ungültig. API-Antwort: {response.text}")

    print_info("Prüfe Branches auf verfügbare Artefakte...")
    branches_with_artifacts = []
    for name in [branch["name"] for branch in branches_json]:
        print(f"  - Prüfe Branch '{name}'...")
        url = f"https://api.github.com/repos/{REPO}/actions/runs?branch={name}&status=success&per_page=1"
        run_response = requests.get(url, headers=headers)
        check_rate_limit(run_response)
        if run_response.status_code == 200 and run_response.json().get("workflow_runs"):
            branches_with_artifacts.append(name)

    if not branches_with_artifacts:
        raise ValueError(
            "Keine Branches mit erfolgreichen Builds und Artefakten gefunden.")

    print(
        f"\n{C.BOLD}Bitte wähle einen Branch aus, von dem installiert werden soll:{C.ENDC}")
    for i, name in enumerate(branches_with_artifacts, 1):
        print(f"  {C.OKCYAN}{i}){C.ENDC} {name}")

    choice = -1
    while not (1 <= choice <= len(branches_with_artifacts)):
        try:
            choice = int(
                input(f"Auswahl (1-{len(branches_with_artifacts)}): "))
        except ValueError:
            pass

    branch = branches_with_artifacts[choice - 1]
    print_info(f"Du hast Branch '{C.OKCYAN}{branch}{C.ENDC}' ausgewählt.")
    return branch


def get_latest_run_info(branch, headers):
    print_info(
        f"Suche nach dem letzten erfolgreichen Workflow-Lauf für Branch '{C.OKCYAN}{branch}{C.ENDC}'...")
    url = f"https://api.github.com/repos/{REPO}/actions/runs?branch={branch}&status=success&per_page=1"
    response = requests.get(url, headers=headers)
    check_rate_limit(response)
    response.raise_for_status()
    runs_json = response.json()

    if not runs_json.get("workflow_runs"):
        raise ValueError(
            "Keine erfolgreichen Workflow-Läufe für diesen Branch gefunden.")
    latest_run = runs_json["workflow_runs"][0]
    remote_version, artifacts_url = latest_run["head_sha"], latest_run["artifacts_url"]
    if not remote_version or not artifacts_url:
        raise ValueError(
            "Konnte die Remote-Versions-ID oder Artefakt-URL nicht ermitteln.")
    return remote_version, artifacts_url


def download_and_extract(name, url, headers, tmp_path, yabridge_dir):
    print_info(f"Lade '{C.OKCYAN}{name}{C.ENDC}' herunter...")
    dl_response = requests.get(
        url, headers=headers, allow_redirects=True, stream=True)
    check_rate_limit(dl_response)
    dl_response.raise_for_status()
    total_size = int(dl_response.headers.get('content-length', 0))
    zip_path = tmp_path / f"{name}.zip"

    with open(zip_path, 'wb') as f:
        if total_size > 0:
            print_progress_bar(
                0, total_size, prefix=f'{C.OKGREEN}Fortschritt:{C.ENDC}', suffix='Komplett', length=40)
        downloaded_size = 0
        for chunk in dl_response.iter_content(chunk_size=8192):
            f.write(chunk)
            downloaded_size += len(chunk)
            if total_size > 0:
                print_progress_bar(
                    downloaded_size, total_size, prefix=f'{C.OKGREEN}Fortschritt:{C.ENDC}', suffix='Komplett', length=40)
    sys.stdout.write('\n')
    sys.stdout.flush()

    if not zipfile.is_zipfile(zip_path):
        raise IOError(
            f"Heruntergeladene Datei für '{name}' ist kein gültiges ZIP-Archiv.")
    with zipfile.ZipFile(zip_path, 'r') as zip_ref:
        zip_ref.extractall(tmp_path / f"{name}_ext")
    tar_path = next((tmp_path / f"{name}_ext").glob('*.tar.gz'), None)
    if not tar_path:
        raise IOError(f"Kein .tar.gz-Archiv im '{name}'-Download gefunden.")

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
        print_header("Installation wird vorbereitet")
        print_info("Rufe Artefakt-Liste ab...")
        response = requests.get(artifacts_url, headers=headers)
        check_rate_limit(response)
        response.raise_for_status()
        artifacts = response.json()["artifacts"]

        ctl_artifact = next(
            (a for a in artifacts if a["name"].startswith("yabridgectl")), None)
        libs_artifact = next(
            (a for a in artifacts if a["name"].startswith("yabridge-")), None)
        if not ctl_artifact or not libs_artifact:
            raise ValueError("Konnte nicht beide Artefakt-URLs finden.")

        backup_base_dir = yabridge_dir.parent / "yabridge-backups"
        if yabridge_dir.exists():
            backup_base_dir.mkdir(exist_ok=True)
            backup_dir = backup_base_dir / \
                f"yabridge-backup-{datetime.datetime.now().strftime('%F-%H%M%S')}"
            print_info(
                f"Sichere bestehende Installation nach {C.OKCYAN}{backup_dir}{C.ENDC}")
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
        print_success(
            f"Update auf Version {C.BOLD}{remote_version[:7]}{C.ENDC} abgeschlossen.")
        print_info(
            f"Installationspfad in {C.OKCYAN}{PATH_CONFIG_FILE}{C.ENDC} gespeichert.")


def run_sync(yabridgectl_path):
    print_header("Synchronisiere Plugins")
    print_info(
        f"Führe '{C.OKCYAN}{yabridgectl_path} sync --prune{C.ENDC}' aus...")
    if not yabridgectl_path.exists():
        raise FileNotFoundError(
            "yabridgectl wurde nach der Installation nicht gefunden.")
    subprocess.run([str(yabridgectl_path), "sync", "--prune"], check=True)


def check_and_update_path(yabridge_dir):
    print_header("PATH-Überprüfung")
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
            print_info(
                f"Pfad '{install_path_str}' ist bereits in '{config_file}' konfiguriert.")
            return

        print_warning(
            f"Der Installationspfad '{install_path_str}' muss zu deinem PATH hinzugefügt werden, um 'yabridgectl' direkt aufrufen zu können.")
        if input(f"{C.WARNING}Soll der Pfad automatisch zu '{config_file}' hinzugefügt werden? (j/N){C.ENDC} ").lower().strip() in ["j", "ja"]:
            with config_file.open("a") as f:
                f.write(f"\n# Added by yabridge-updater\n{line_to_add}\n")
            print_success(
                f"Pfad wurde hinzugefügt. Bitte starte dein Terminal neu oder führe 'source {config_file}' aus, damit die Änderungen wirksam werden.")
        else:
            print_info(
                "Automatisches Hinzufügen übersprungen. Bitte füge den Pfad manuell hinzu.")
    else:
        print_warning(
            f"Unbekannte Shell '{shell_name}'. Bitte füge den Pfad '{install_path_str}' manuell zu deinem PATH hinzu.")


def prune_backups(backup_parent_dir, keep_count):
    backup_base_dir = backup_parent_dir / "yabridge-backups"
    print_header("Alte Backups aufräumen")
    backups = sorted([d for d in backup_base_dir.glob("yabridge-backup-*")
                     if d.is_dir()], key=lambda d: d.name, reverse=True)

    if len(backups) <= keep_count:
        print_info("Nicht genügend alte Backups zum Aufräumen gefunden.")
        return

    to_delete = backups[keep_count:]
    print_info(f"Lösche {len(to_delete)} alte Backup(s)...")
    for backup_dir in to_delete:
        try:
            shutil.rmtree(backup_dir)
            print(f"  - {C.OKCYAN}{backup_dir.name}{C.ENDC} gelöscht.")
        except OSError as e:
            print_error(f"Konnte Backup {backup_dir} nicht löschen", details=e)
    print_success("Aufräumen der Backups abgeschlossen.")


def restore_from_backup(yabridge_dir):
    print_header("Backup wiederherstellen")
    backup_base_dir = yabridge_dir.parent / "yabridge-backups"
    backups = sorted([d for d in backup_base_dir.glob("yabridge-backup-*")
                     if d.is_dir()], key=lambda d: d.name, reverse=True)

    if not backups:
        raise FileNotFoundError("Keine Backups zum Wiederherstellen gefunden.")

    print(f"\n{C.BOLD}Verfügbare Backups (neueste zuerst):{C.ENDC}")
    for i, backup in enumerate(backups, 1):
        version_str = ""
        version_file_in_backup = backup / ".version"
        if version_file_in_backup.is_file():
            try:
                version_data = json.loads(version_file_in_backup.read_text())
                version_sha, version_branch = version_data.get(
                    "sha", "N/A")[:7], version_data.get("branch", "N/A")
                version_str = f" (Version: {C.OKGREEN}{version_sha}{C.ENDC}, Branch: {C.OKCYAN}{version_branch}{C.ENDC})"
            except json.JSONDecodeError:
                version_str = f" {C.FAIL}(Ungültige Versionsdatei){C.ENDC}"
        date_str = backup.name.replace("yabridge-backup-", "")
        print(f"  {C.OKCYAN}{i}){C.ENDC} {date_str}{version_str}")

    choice = -1
    while not (1 <= choice <= len(backups)):
        try:
            choice = int(
                input(f"Welches Backup wiederherstellen? (1-{len(backups)}): "))
        except ValueError:
            pass

    selected_backup = backups[choice - 1]
    print_info(
        f"'{C.OKCYAN}{selected_backup.name}{C.ENDC}' wird wiederhergestellt...")

    backup_base_dir.mkdir(exist_ok=True)
    if yabridge_dir.exists():
        pre_restore_backup_dir = backup_base_dir / \
            f"yabridge-pre-restore-backup-{datetime.datetime.now().strftime('%F-%H%M%S')}"
        print_info(
            f"Sichere die aktuelle Installation nach {C.OKCYAN}{pre_restore_backup_dir}{C.ENDC}...")
        shutil.move(str(yabridge_dir), str(pre_restore_backup_dir))

    try:
        shutil.move(str(selected_backup), str(yabridge_dir))
        if (yabridge_dir / ".version").is_file():
            print_info(
                "Installation inklusive .version-Datei wiederhergestellt.")
        print_success("Wiederherstellung erfolgreich!")
    except OSError as e:
        print_error("Wiederherstellung fehlgeschlagen", details=e)
        if 'pre_restore_backup_dir' in locals() and pre_restore_backup_dir.exists():
            print_info(
                "Versuche, die ursprüngliche Installation wiederherzustellen...")
            # No need to call check_and_update_path here, as the path hasn't changed.
            shutil.move(str(pre_restore_backup_dir), str(yabridge_dir))
        sys.exit(1)


def handle_arguments():
    parser = argparse.ArgumentParser(
        description="Ein Skript zum Herunterladen und Verwalten von Entwicklerversionen von yabridge.", formatter_class=argparse.RawTextHelpFormatter)
    parser.add_argument("--install-path", type=Path, default=None,
                        help="Benutzerdefinierter Installationspfad für yabridge. Überschreibt gespeicherte Pfade.")
    subparsers = parser.add_subparsers(dest="command", title="Befehle")

    update_parser = subparsers.add_parser(
        "update", help="Sucht nach Updates und installiert sie (Standardaktion).")
    update_parser.add_argument("--interactive", action="store_true",
                               help="Erzwingt die interaktive Auswahl eines Branches.")
    subparsers.add_parser(
        "status", help="Zeigt die aktuell installierte Version und den Pfad an.")
    subparsers.add_parser(
        "restore", help="Stellt eine frühere Version aus einem Backup wieder her.")
    prune_parser = subparsers.add_parser(
        "prune-backups", help="Löscht alte Backups.")
    prune_parser.add_argument("keep", type=int, nargs="?", default=5,
                              help="Anzahl der zu behaltenden Backups (Standard: 5).")
    token_parser = subparsers.add_parser(
        "token", help="Verwaltet den gespeicherten GitHub-Token.")
    token_parser.add_argument(
        "--clear", action="store_true", help="Löscht den gespeicherten GitHub-Token.")
    return parser.parse_args()


def determine_install_path(args):
    if args.install_path:
        yabridge_dir = args.install_path.resolve()
        print_info(
            f"Verwende benutzerdefinierten Installationspfad: {C.OKCYAN}{args.install_path}{C.ENDC}")
    elif PATH_CONFIG_FILE.exists() and PATH_CONFIG_FILE.read_text().strip():
        yabridge_dir = Path(PATH_CONFIG_FILE.read_text().strip()).resolve()
        print_info(
            f"Verwende gespeicherten Installationspfad: {C.OKCYAN}{yabridge_dir}{C.ENDC}")
    else:
        yabridge_dir = HOME / ".local" / "share" / "yabridge"
        print_info(
            f"Verwende Standard-Installationspfad: {C.OKCYAN}{yabridge_dir}{C.ENDC}")
    return yabridge_dir, yabridge_dir / "yabridgectl"

# --- Main Execution ---


def main():
    """Main script logic."""
    args = handle_arguments()
    command = args.command if args.command else 'update'
    yabridge_dir, yabridgectl_path = determine_install_path(args)

    try:
        if command == 'status':
            print_header("Status der yabridge-Installation")
            print(f"  Installationspfad: {C.OKCYAN}{yabridge_dir}{C.ENDC}")
            if yabridgectl_path.exists():
                print(f"  yabridgectl gefunden: {C.OKGREEN}Ja{C.ENDC}")
            else:
                print(
                    f"  yabridgectl gefunden: {C.FAIL}Nein (Installation ist beschädigt oder nicht vorhanden){C.ENDC}")
            version_file_in_install = yabridge_dir / ".version"
            if version_file_in_install.is_file():
                try:
                    version_data = json.loads(
                        version_file_in_install.read_text())
                    print(
                        f"  Installierter Branch: {C.OKCYAN}{version_data.get('branch', 'N/A')}{C.ENDC}")
                    print(
                        f"  Installierte Version (SHA): {C.OKGREEN}{version_data.get('sha', 'N/A')}{C.ENDC}")
                except json.JSONDecodeError:
                    print_error("Lokale .version-Datei ist korrupt.")
            else:
                print(
                    f"  Version: {C.WARNING}Unbekannt (keine .version-Datei gefunden){C.ENDC}")
            sys.exit(0)

        if command == 'restore':
            restore_from_backup(yabridge_dir)
            run_sync(yabridgectl_path)
            check_and_update_path(yabridge_dir)  # Check path after restore
            print_success("Wiederherstellungsprozess abgeschlossen.")
            sys.exit(0)

        if command == 'prune-backups':
            prune_backups(yabridge_dir.parent, args.keep)
            sys.exit(0)

        if command == 'token':
            if args.clear:
                clear_tokens()
            else:
                print_info("Verwende 'token --clear' zum Löschen des Tokens.")
            sys.exit(0)

        if command == 'update':
            print_header("Yabridge Updater")
            token, token_source = get_token()
            if not token:
                raise ValueError("Kein GitHub Token verfügbar. Abbruch.")
            headers = {"Authorization": f"Bearer {token}",
                       "Accept": "application/vnd.github.v3+json"}

            version_file_in_install = yabridge_dir / ".version"
            local_info, is_interactive = None, getattr(
                args, 'interactive', False)

            if is_interactive:
                print_info("Interaktiver Modus wird erzwungen.")
            elif version_file_in_install.is_file():
                try:
                    local_info = json.loads(
                        version_file_in_install.read_text())
                except json.JSONDecodeError:
                    print_warning(
                        "Lokale .version-Datei ist korrupt. Wechsle in den interaktiven Modus.")
                    is_interactive = True

            if not is_interactive and local_info and local_info.get("branch") and local_info.get("sha"):
                local_branch, local_sha = local_info["branch"], local_info["sha"]
                print_info(
                    f"Prüfe auf Updates für den installierten Branch '{C.OKCYAN}{local_branch}{C.ENDC}'...")
                remote_sha, artifacts_url = get_latest_run_info(
                    local_branch, headers)

                if remote_sha != local_sha:
                    print_info(
                        f"Update von {C.WARNING}{local_sha[:7]}{C.ENDC} auf {C.OKGREEN}{remote_sha[:7]}{C.ENDC} für Branch '{local_branch}' verfügbar.")
                    if input(f"{C.WARNING}Jetzt installieren? (J/n){C.ENDC} ").lower().strip() in ["", "j", "ja"]:
                        perform_installation(
                            artifacts_url, headers, yabridge_dir, remote_sha, local_branch)
                        check_and_update_path(yabridge_dir)
                        run_sync(yabridgectl_path)
                    else:
                        print_info("Update abgebrochen.")
                else:
                    print_success("Du hast bereits die aktuellste Version.")
            else:
                print_info(
                    "Keine lokale Version gefunden oder --interactive gesetzt. Starte interaktiven Modus...")
                branch = select_branch(headers, token_source)
                remote_version, artifacts_url = get_latest_run_info(
                    branch, headers)
                perform_installation(artifacts_url, headers,
                                     yabridge_dir, remote_version, branch)
                check_and_update_path(yabridge_dir)
                run_sync(yabridgectl_path)

    except requests.RequestException as e:
        print_error(
            "Ein Netzwerkfehler bei der Kommunikation mit GitHub ist aufgetreten.", details=e)
    except subprocess.SubprocessError as e:
        print_error(
            "Ein externer Befehl (z.B. yabridgectl) ist fehlgeschlagen.", details=e)
    except (IOError, zipfile.BadZipFile, tarfile.TarError) as e:
        print_error(
            "Ein Fehler beim Lesen, Schreiben oder Entpacken von Dateien ist aufgetreten.", details=e)
    except (FileNotFoundError, ValueError) as e:
        print_error(
            "Ein interner Fehler oder eine unerwartete API-Antwort ist aufgetreten.", details=e)
    except Exception as e:
        print_error(
            "Ein unerwarteter, allgemeiner Fehler ist aufgetreten", details=e)
        sys.exit(1)

    print_success("Skript erfolgreich beendet.")


if __name__ == "__main__":
    try:
        import requests
    except ImportError:
        print_error(
            "Das 'requests' Modul wird benötigt. Bitte installiere es mit z.B. 'pip install requests', 'sudo pacman -S python-requests' oder 'sudo apt install python3-requests'. Je nach Distro kann es verschiedene Installationsmethoden geben. ")
        sys.exit(1)
    main()
