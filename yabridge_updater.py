#!/usr/bin/env python3
import argparse
import datetime
import getpass
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
VERSION_FILE = CONFIG_DIR / "version"
PATH_CONFIG_FILE = CONFIG_DIR / "path"

# --- Helper Functions ---

def print_error(message):
    """Prints an error message to stderr."""
    print(f"FEHLER: {message}", file=sys.stderr)

def print_info(message):
    """Prints an informational message."""
    print(f"-> {message}")

def print_progress_bar(iteration, total, prefix='', suffix='', decimals=1, length=50, fill='█'):
    """Call in a loop to create terminal progress bar."""
    if total == 0: total = 1
    percent = ("{0:." + str(decimals) + "f}").format(100 * (iteration / float(total)))
    filled_length = int(length * iteration // total)
    bar = fill * filled_length + '-' * (length - filled_length)
    sys.stdout.write(f'\r{prefix} |{bar}| {percent}% {suffix}')
    sys.stdout.flush()

def check_command_exists(cmd):
    """Checks if a command exists on the system."""
    return shutil.which(cmd) is not None

# --- Token Management ---

def get_github_token_from_keyring():
    if not check_command_exists("secret-tool"): return None
    try:
        result = subprocess.run(["secret-tool", "lookup", "service", "yabridge-updater"], capture_output=True, text=True, check=False)
        if result.returncode == 0 and result.stdout.strip():
            print_info("GitHub Token aus dem System-Schlüsselbund geladen.")
            return result.stdout.strip()
    except (subprocess.SubprocessError, FileNotFoundError): pass
    return None

def get_github_token_from_file():
    if not TOKEN_FILE.exists(): return None
    if not check_command_exists("openssl"): 
        print_error("'openssl' wird zum Entschlüsseln benötigt, ist aber nicht installiert.")
        return None
    print_info("Verschlüsselte Token-Datei gefunden (openssl-Fallback).")
    password = getpass.getpass("Bitte das Passwort zum Entschlüsseln des Tokens eingeben: ")
    try:
        process = subprocess.run(["openssl", "enc", "-aes-256-cbc", "-a", "-d", "-salt", "-pbkdf2", "-pass", f"pass:{password}"], input=TOKEN_FILE.read_text(), capture_output=True, text=True, check=True)
        decrypted_token = process.stdout.strip()
        if not decrypted_token: print_error("Entschlüsselung fehlgeschlagen.")
        return decrypted_token
    except (subprocess.SubprocessError, FileNotFoundError) as e:
        print_error(f"Entschlüsselung fehlgeschlagen: {e}")
    return None

def save_token_to_keyring(token):
    try:
        subprocess.run(["secret-tool", "store", "--label=yabridge-updater GitHub PAT", "service", "yabridge-updater"], input=token, text=True, check=True, capture_output=True)
        print_info("Token wurde sicher im System-Schlüsselbund gespeichert.")
    except (subprocess.SubprocessError, FileNotFoundError):
        print_error("Speichern des Tokens im Schlüsselbund fehlgeschlagen.")

def save_token_to_file(token):
    password = getpass.getpass("Bitte ein Passwort zum Verschlüsseln des Tokens eingeben: ")
    if password != getpass.getpass("Passwort bestätigen: "):
        print_error("Passwörter stimmen nicht überein. Token wird nicht gespeichert.")
        return
    try:
        process = subprocess.run(["openssl", "enc", "-aes-256-cbc", "-a", "-salt", "-pbkdf2", "-pass", f"pass:{password}"], input=token, capture_output=True, text=True, check=True)
        CONFIG_DIR.mkdir(exist_ok=True)
        TOKEN_FILE.write_text(process.stdout)
        TOKEN_FILE.chmod(0o600)
        print_info("Token wurde verschlüsselt (mit openssl) gespeichert.")
    except (subprocess.SubprocessError, FileNotFoundError):
        print_error("Verschlüsselung mit openssl fehlgeschlagen. Token nicht gespeichert.")

def get_token():
    token = os.environ.get("GITHUB_TOKEN")
    if token: return token, "env"
    token = get_github_token_from_keyring()
    if token: return token, "keyring"
    token = get_github_token_from_file()
    if token: return token, "file"
    
    print_info("GitHub-API-Authentifizierung ist erforderlich.")
    token = getpass.getpass("Gib dein GitHub PAT ein: ")
    if not token: return None, None

    if input("Soll das neue Token für die zukünftige Nutzung gespeichert werden? (j/N) ").lower() in ["j", "ja"]:
        if check_command_exists("secret-tool"): save_token_to_keyring(token)
        elif check_command_exists("openssl"): save_token_to_file(token)
        else: print_error("Weder 'secret-tool' noch 'openssl' gefunden. Token kann nicht sicher gespeichert werden.")
    return token, "prompt"

def clear_tokens():
    print_info("Lösche gespeicherte GitHub-Tokens...")
    if check_command_exists("secret-tool") and subprocess.run(["secret-tool", "lookup", "service", "yabridge-updater"], capture_output=True).returncode == 0:
        print_info("Gespeichertes Token im Schlüsselbund gefunden. Versuche zu löschen...")
        subprocess.run(["secret-tool", "clear", "service", "yabridge-updater"], check=False)
        if subprocess.run(["secret-tool", "lookup", "service", "yabridge-updater"], capture_output=True).returncode == 0:
            print_error("Konnte das Token nicht automatisch aus dem Schlüsselbund löschen. Bitte manuell entfernen.")
        else:
            print_info("Token erfolgreich aus dem System-Schlüsselbund entfernt.")
    if TOKEN_FILE.exists():
        TOKEN_FILE.unlink()
        print_info("Verschlüsselte Token-Datei (openssl-Fallback) entfernt.")
    print_info("Token-Löschvorgang abgeschlossen.")

# --- Core Logic Functions ---

def select_branch(headers, token_source):
    print_info("Lade verfügbare Branches...")
    response = requests.get(f"https://api.github.com/repos/{REPO}/branches", headers=headers)
    response.raise_for_status()
    branches_json = response.json()

    if not isinstance(branches_json, list) or not branches_json:
        print_error(f"Konnte keine gültige Branch-Liste von GitHub abrufen. Der Token ist möglicherweise ungültig. API-Antwort: {response.text}")
        if token_source in ["keyring", "file"]: clear_tokens()
        sys.exit(1)

    print_info("Prüfe Branches auf verfügbare Artefakte...")
    branches_with_artifacts = []
    for name in [branch["name"] for branch in branches_json]:
        print(f"  - Prüfe Branch '{name}'...")
        url = f"https://api.github.com/repos/{REPO}/actions/runs?branch={name}&status=success&per_page=1"
        run_response = requests.get(url, headers=headers)
        if run_response.status_code == 200 and run_response.json().get("workflow_runs"):
            branches_with_artifacts.append(name)

    if not branches_with_artifacts:
        print_error("Keine Branches mit erfolgreichen Builds und Artefakten gefunden.")
        sys.exit(1)

    print("\nBitte wähle einen Branch aus, von dem installiert werden soll:")
    for i, name in enumerate(branches_with_artifacts, 1):
        print(f"{i}) {name}")

    choice = -1
    while not (1 <= choice <= len(branches_with_artifacts)):
        try: choice = int(input(f"Auswahl (1-{len(branches_with_artifacts)}): "))
        except ValueError: pass
    
    branch = branches_with_artifacts[choice - 1]
    print_info(f"Du hast Branch '{branch}' ausgewählt.")
    return branch

def get_latest_run_info(branch, headers):
    print_info(f"Suche nach dem letzten erfolgreichen Workflow-Lauf für Branch '{branch}'...")
    url = f"https://api.github.com/repos/{REPO}/actions/runs?branch={branch}&status=success&per_page=1"
    response = requests.get(url, headers=headers)
    response.raise_for_status()
    runs_json = response.json()

    if not runs_json.get("workflow_runs"):
        print_error("Keine erfolgreichen Workflow-Läufe für diesen Branch gefunden.")
        sys.exit(1)

    latest_run = runs_json["workflow_runs"][0]
    remote_version = latest_run["head_sha"]
    artifacts_url = latest_run["artifacts_url"]

    if not remote_version or not artifacts_url:
        print_error("Konnte die Remote-Versions-ID oder Artefakt-URL nicht ermitteln.")
        sys.exit(1)
    return remote_version, artifacts_url

def download_and_extract(name, url, headers, tmp_path, yabridge_dir):
    print_info(f"Lade '{name}' herunter...")
    dl_response = requests.get(url, headers=headers, allow_redirects=True, stream=True)
    dl_response.raise_for_status()

    total_size = int(dl_response.headers.get('content-length', 0))
    zip_path = tmp_path / f"{name}.zip"
    
    downloaded_size = 0
    with open(zip_path, 'wb') as f:
        if total_size > 0: print_progress_bar(0, total_size, prefix='Fortschritt:', suffix='Komplett', length=40)
        for chunk in dl_response.iter_content(chunk_size=8192):
            f.write(chunk)
            downloaded_size += len(chunk)
            if total_size > 0: print_progress_bar(downloaded_size, total_size, prefix='Fortschritt:', suffix='Komplett', length=40)
    sys.stdout.write('\n'); sys.stdout.flush()

    if not zipfile.is_zipfile(zip_path): raise IOError(f"Heruntergeladene Datei für '{name}' ist kein gültiges ZIP-Archiv.")

    with zipfile.ZipFile(zip_path, 'r') as zip_ref:
        zip_ref.extractall(tmp_path / f"{name}_ext")

    tar_path = next((tmp_path / f"{name}_ext").glob('*.tar.gz'), None)
    if not tar_path: raise IOError(f"Kein .tar.gz-Archiv im '{name}'-Download gefunden.")

    with tarfile.open(tar_path, "r:gz") as tar:
        def strip_filter(member, path):
            try:
                new_parts = Path(member.name).parts[1:]
                if not new_parts: return None
                member.name = str(Path(*new_parts))
            except IndexError: return None
            return member
        if sys.version_info >= (3, 12): tar.extractall(path=yabridge_dir, filter=strip_filter)
        else:
            members = [m for m in [strip_filter(m, '') for m in tar.getmembers()] if m is not None]
            tar.extractall(path=yabridge_dir, members=members)

def perform_installation(artifacts_url, headers, yabridge_dir, remote_version):
    with tempfile.TemporaryDirectory() as tmpdir:
        tmp_path = Path(tmpdir)
        print_info("Rufe Artefakt-Liste ab...")
        response = requests.get(artifacts_url, headers=headers)
        response.raise_for_status()
        artifacts = response.json()["artifacts"]

        ctl_artifact = next((a for a in artifacts if a["name"].startswith("yabridgectl")), None)
        libs_artifact = next((a for a in artifacts if a["name"].startswith("yabridge-")), None)
        if not ctl_artifact or not libs_artifact: raise ValueError("Konnte nicht beide Artefakt-URLs finden.")

        if yabridge_dir.exists():
            backup_dir = yabridge_dir.parent / f"yabridge-backup-{datetime.datetime.now().strftime('%F-%H%M%S')}"
            print_info(f"Sichere bestehende Installation nach {backup_dir}")
            shutil.move(str(yabridge_dir), str(backup_dir))
        yabridge_dir.mkdir(parents=True, exist_ok=True)

        download_and_extract("ctl", ctl_artifact["archive_download_url"], headers, tmp_path, yabridge_dir)
        download_and_extract("libs", libs_artifact["archive_download_url"], headers, tmp_path, yabridge_dir)

        CONFIG_DIR.mkdir(exist_ok=True)
        VERSION_FILE.write_text(remote_version)
        PATH_CONFIG_FILE.write_text(str(yabridge_dir))
        print_info(f"Update auf Version {remote_version} abgeschlossen.")
        print_info(f"Installationspfad in {PATH_CONFIG_FILE} gespeichert.")

def run_sync(yabridgectl_path):
    print_info(f"Führe '{yabridgectl_path} sync --prune' aus...")
    if not yabridgectl_path.exists(): raise FileNotFoundError("yabridgectl wurde nach der Installation nicht gefunden.")
    subprocess.run([str(yabridgectl_path), "sync", "--prune"], check=True)

def check_and_update_path(yabridge_dir):
    print_info("Überprüfe und füge den Installationspfad zum PATH hinzu...")
    install_path_str = str(yabridge_dir)
    if install_path_str in os.environ.get("PATH", "").split(os.pathsep): 
        print_info(f"Pfad '{install_path_str}' ist bereits im PATH vorhanden.")
        return

    shell_name = Path(os.environ.get("SHELL", "")).name
    config_file, line_to_add = None, None
    if shell_name == "bash":
        config_file, line_to_add = HOME / ".bashrc", f'export PATH="{install_path_str}:$PATH"'
    elif shell_name == "zsh":
        config_file, line_to_add = HOME / ".zshrc", f'export PATH="{install_path_str}:$PATH"'
    elif shell_name == "fish":
        config_file, line_to_add = HOME / ".config" / "fish" / "config.fish", f"fish_add_path {install_path_str}"

    if config_file and line_to_add and (not config_file.exists() or line_to_add not in config_file.read_text()):
        print_info(f"Füge Pfad für {shell_name} in {config_file} hinzu.")
        with config_file.open("a") as f: f.write(f"\n# Added by yabridge-updater\n{line_to_add}\n")
        print_info(f"Bitte starte dein Terminal neu oder führe 'source {config_file}' aus.")
    elif config_file: print_info(f"Pfad ist bereits in {config_file} vorhanden.")
    else: print_info(f"Unbekannte Shell '{shell_name}'. Bitte füge den Pfad '{install_path_str}' manuell zu deinem PATH hinzu.")

def prune_backups(backup_parent_dir, keep_count):
    print_info(f"Räume Backups auf, behalte die letzten {keep_count}...")
    backups = sorted([d for d in backup_parent_dir.glob("yabridge-backup-*") if d.is_dir()], key=lambda d: d.name, reverse=True)

    if len(backups) <= keep_count:
        print_info("Nicht genügend alte Backups zum Aufräumen gefunden.")
        return

    to_delete = backups[keep_count:]
    print_info(f"Lösche {len(to_delete)} alte Backup(s)...")
    for backup_dir in to_delete:
        try:
            shutil.rmtree(backup_dir)
            print(f"  - {backup_dir.name} gelöscht.")
        except OSError as e:
            print_error(f"Konnte Backup {backup_dir} nicht löschen: {e}")

def handle_arguments():
    parser = argparse.ArgumentParser(description="Lädt die neueste Entwicklerversion von yabridge herunter.", formatter_class=argparse.RawTextHelpFormatter)
    parser.add_argument("--update-token", action="store_true", help="Gespeicherte GitHub-Tokens löschen und neu eingeben.")
    parser.add_argument("--install-path", type=Path, default=None, help="Benutzerdefinierter Installationspfad für yabridge.\nStandard: ~/.local/share/yabridge")
    parser.add_argument("--prune-backups", type=int, nargs='?', const=5, default=None, metavar='N', help="Lösche alte Backups und behalte nur die letzten N.\nStandard, wenn Flag gesetzt ist: 5.")
    parser.add_argument("--status", action="store_true", help="Zeigt die aktuell installierte Version und den Pfad an, ohne ein Update auszuführen.")
    return parser.parse_args()

def determine_install_path(args):
    if args.install_path:
        yabridge_dir = args.install_path.resolve()
        print_info(f"Verwende benutzerdefinierten Installationspfad (via Parameter): {yabridge_dir}")
    elif PATH_CONFIG_FILE.exists() and PATH_CONFIG_FILE.read_text().strip():
        yabridge_dir = Path(PATH_CONFIG_FILE.read_text().strip()).resolve()
        print_info(f"Verwende gespeicherten Installationspfad: {yabridge_dir}")
    else:
        yabridge_dir = HOME / ".local" / "share" / "yabridge"
        print_info(f"Verwende Standard-Installationspfad: {yabridge_dir}")
    return yabridge_dir, yabridge_dir / "yabridgectl"

# --- Main Execution ---

def main():
    """Main script logic."""
    args = handle_arguments()
    yabridge_dir, yabridgectl_path = determine_install_path(args)

    if args.status:
        print_info("Status der yabridge-Installation:")
        print(f"  Installationspfad: {yabridge_dir}")
        if yabridgectl_path.exists():
            print(f"  yabridgectl gefunden: Ja")
        else:
            print(f"  yabridgectl gefunden: Nein (Installation ist beschädigt oder nicht vorhanden)")
        if VERSION_FILE.exists():
            local_version = VERSION_FILE.read_text().strip()
            print(f"  Installierte Version (SHA): {local_version}")
        else:
            print("  Installierte Version (SHA): Unbekannt (keine Versionsdatei gefunden)")
        sys.exit(0)

    if args.update_token: 
        clear_tokens()
        sys.exit(0)

    token, token_source = get_token()
    if not token: 
        print_error("Kein GitHub Token verfügbar. Abbruch.")
        sys.exit(1)

    headers = {"Authorization": f"Bearer {token}", "Accept": "application/vnd.github.v3+json"}

    try:
        branch = select_branch(headers, token_source)
        remote_version, artifacts_url = get_latest_run_info(branch, headers)
        local_version = VERSION_FILE.read_text().strip() if VERSION_FILE.exists() else ""

        if remote_version == local_version and yabridgectl_path.exists():
            print_info(f"Du hast bereits die aktuellste Version ({remote_version}) und die Installation ist intakt.")
        else:
            if not yabridgectl_path.exists() and remote_version == local_version:
                print_info(f"Die Version ({local_version}) ist aktuell, aber die Installation ist beschädigt. Führe Reparatur durch...")
            else:
                print_info(f"Neue Version gefunden: {remote_version} (installiert: {local_version or 'keine'})")
            perform_installation(artifacts_url, headers, yabridge_dir, remote_version)

        run_sync(yabridgectl_path)
        check_and_update_path(yabridge_dir)

        if args.prune_backups is not None:
            prune_backups(yabridge_dir.parent, args.prune_backups)

    except (requests.RequestException, subprocess.SubprocessError, FileNotFoundError, ValueError, IOError, zipfile.BadZipFile, tarfile.TarError) as e:
        print_error(f"Ein Fehler ist aufgetreten: {e}")
        sys.exit(1)

    print_info("Skript erfolgreich beendet.")

if __name__ == "__main__":
    try:
        import requests
    except ImportError:
        print_error("Das 'requests' Modul wird benötigt. Bitte installiere es mit 'pip install requests'.")
        sys.exit(1)
    main()
