#!/usr/bin/env python3
import argparse
import base64
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
YABRIDGE_DIR = HOME / ".local" / "share" / "yabridge"
YABRIDGECTL_PATH = YABRIDGE_DIR / "yabridgectl"
CONFIG_DIR = HOME / ".config" / "yabridge-updater"
TOKEN_FILE = CONFIG_DIR / "token"
VERSION_FILE = CONFIG_DIR / "version"

def print_error(message):
    """Prints an error message to stderr."""
    print(f"FEHLER: {message}", file=sys.stderr)

def print_info(message):
    """Prints an informational message."""
    print(f"-> {message}")

def check_command_exists(cmd):
    """Checks if a command exists on the system."""
    return shutil.which(cmd) is not None

def get_github_token_from_keyring():
    """Tries to get the GitHub token from the system keyring via secret-tool."""
    if not check_command_exists("secret-tool"):
        return None
    try:
        result = subprocess.run(
            ["secret-tool", "lookup", "service", "yabridge-updater"],
            capture_output=True,
            text=True,
            check=False,
        )
        if result.returncode == 0 and result.stdout.strip():
            print_info("GitHub Token aus dem System-Schlüsselbund geladen.")
            return result.stdout.strip()
    except (subprocess.SubprocessError, FileNotFoundError):
        pass
    return None

def get_github_token_from_file():
    """Tries to get the GitHub token from the encrypted file."""
    if not TOKEN_FILE.exists():
        return None
    if not check_command_exists("openssl"):
        print_error("'openssl' wird zum Entschlüsseln benötigt, ist aber nicht installiert.")
        return None

    print_info("Verschlüsselte Token-Datei gefunden (openssl-Fallback).")
    password = getpass.getpass("Bitte das Passwort zum Entschlüsseln des Tokens eingeben: ")
    encrypted_token = TOKEN_FILE.read_text()
    try:
        process = subprocess.run(
            [
                "openssl", "enc", "-aes-256-cbc", "-a", "-d", "-salt", "-pbkdf2",
                "-pass", f"pass:{password}"
            ],
            input=encrypted_token,
            capture_output=True,
            text=True,
            check=True,
        )
        decrypted_token = process.stdout.strip()
        if not decrypted_token:
            print_error("Entschlüsselung fehlgeschlagen.")
            return None
        return decrypted_token
    except (subprocess.SubprocessError, FileNotFoundError) as e:
        print_error(f"Entschlüsselung fehlgeschlagen: {e}")
        return None

def save_token_to_keyring(token):
    """Saves the token to the system keyring."""
    try:
        subprocess.run(
            ["secret-tool", "store", "--label=yabridge-updater GitHub PAT", "service", "yabridge-updater"],
            input=token,
            text=True,
            check=True,
            capture_output=True,
        )
        print_info("Token wurde sicher im System-Schlüsselbund gespeichert.")
    except (subprocess.SubprocessError, FileNotFoundError):
        print_error("Speichern des Tokens im Schlüsselbund fehlgeschlagen.")

def save_token_to_file(token):
    """Encrypts and saves the token to a file."""
    password = getpass.getpass("Bitte ein Passwort zum Verschlüsseln des Tokens eingeben: ")
    password_confirm = getpass.getpass("Passwort bestätigen: ")
    if password != password_confirm:
        print_error("Passwörter stimmen nicht überein. Token wird nicht gespeichert.")
        return

    try:
        process = subprocess.run(
            [
                "openssl", "enc", "-aes-256-cbc", "-a", "-salt", "-pbkdf2",
                "-pass", f"pass:{password}"
            ],
            input=token,
            capture_output=True,
            text=True,
            check=True,
        )
        CONFIG_DIR.mkdir(exist_ok=True)
        TOKEN_FILE.write_text(process.stdout)
        TOKEN_FILE.chmod(0o600)
        print_info("Token wurde verschlüsselt (mit openssl) gespeichert.")
    except (subprocess.SubprocessError, FileNotFoundError):
        print_error("Verschlüsselung mit openssl fehlgeschlagen. Token nicht gespeichert.")


def get_token():
    """Gets the GitHub token from env, keyring, or file, or prompts the user."""
    # 1. Environment variable
    token = os.environ.get("GITHUB_TOKEN")
    if token:
        print_info("GitHub Token aus der Umgebungsvariable GITHUB_TOKEN verwendet.")
        return token, "env"

    # 2. System keyring
    token = get_github_token_from_keyring()
    if token:
        return token, "keyring"

    # 3. Encrypted file
    token = get_github_token_from_file()
    if token:
        return token, "file"

    # 4. Prompt user
    print_info("GitHub-API-Authentifizierung ist erforderlich.")
    token = getpass.getpass("Gib dein GitHub PAT ein: ")
    if not token:
        return None, None

    save_choice = input("Soll das neue Token für die zukünftige Nutzung gespeichert werden? (j/N) ").lower()
    if save_choice in ["j", "ja"]:
        if check_command_exists("secret-tool"):
            save_token_to_keyring(token)
        elif check_command_exists("openssl"):
            save_token_to_file(token)
        else:
            print_error("Weder 'secret-tool' noch 'openssl' gefunden. Token kann nicht sicher gespeichert werden.")

    return token, "prompt"

def clear_tokens():
    """Clears stored GitHub tokens from keyring and file."""
    print_info("Lösche gespeicherte GitHub-Tokens...")
    # Clear from keyring
    if check_command_exists("secret-tool"):
        # Check if it exists before trying to clear
        result = subprocess.run(["secret-tool", "lookup", "service", "yabridge-updater"], capture_output=True)
        if result.returncode == 0:
            print_info("Gespeichertes Token im Schlüsselbund gefunden. Versuche zu löschen...")
            subprocess.run(["secret-tool", "clear", "service", "yabridge-updater"], check=False)
            # Verify deletion
            result_after = subprocess.run(["secret-tool", "lookup", "service", "yabridge-updater"], capture_output=True)
            if result_after.returncode == 0:
                 print_error("Konnte das Token nicht automatisch aus dem Schlüsselbund löschen. Bitte manuell entfernen.")
            else:
                 print_info("Token erfolgreich aus dem System-Schlüsselbund entfernt.")
        else:
            print_info("Kein Token im System-Schlüsselbund gefunden.")

    # Clear from file
    if TOKEN_FILE.exists():
        TOKEN_FILE.unlink()
        print_info("Verschlüsselte Token-Datei (openssl-Fallback) entfernt.")
    print_info("Token-Löschvorgang abgeschlossen.")


def main():
    """Main script logic."""
    parser = argparse.ArgumentParser(description="Lädt die neueste Entwicklerversion von yabridge herunter.")
    parser.add_argument("--update-token", action="store_true", help="Gespeicherte GitHub-Tokens löschen und neu eingeben.")
    args = parser.parse_args()

    if args.update_token:
        clear_tokens()
        sys.exit(0)

    # --- 1. Get Token ---
    token, token_source = get_token()
    if not token:
        print_error("Kein GitHub Token verfügbar. Abbruch.")
        sys.exit(1)

    headers = {
        "Authorization": f"Bearer {token}",
        "Accept": "application/vnd.github.v3+json",
    }

    # --- 2. Select Branch ---
    try:
        print_info("Lade verfügbare Branches...")
        response = requests.get(f"https://api.github.com/repos/{REPO}/branches", headers=headers)
        response.raise_for_status()
        branches_json = response.json()

        if not isinstance(branches_json, list) or not branches_json:
            print_error("Konnte keine gültige Branch-Liste von GitHub abrufen. Der Token ist möglicherweise ungültig.")
            print_error(f"API-Antwort: {response.text}")
            if token_source in ["keyring", "file"]:
                clear_tokens()
            sys.exit(1)

        branch_names = [branch["name"] for branch in branches_json]
        print("Bitte wähle einen Branch aus, von dem installiert werden soll:")
        for i, name in enumerate(branch_names, 1):
            print(f"{i}) {name}")

        choice = -1
        while choice < 1 or choice > len(branch_names):
            try:
                choice = int(input(f"Auswahl (1-{len(branch_names)}): "))
            except ValueError:
                pass
        branch = branch_names[choice - 1]
        print_info(f"Du hast Branch '{branch}' ausgewählt.")

    except requests.RequestException as e:
        print_error(f"Fehler bei der Kommunikation mit der GitHub-API: {e}")
        sys.exit(1)


    # --- 3. Get Latest Workflow Run ---
    try:
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

    except requests.RequestException as e:
        print_error(f"Fehler beim Abrufen der Workflow-Informationen: {e}")
        sys.exit(1)

    # --- 4. Version Check and Installation ---
    local_version = VERSION_FILE.read_text().strip() if VERSION_FILE.exists() else ""

    if remote_version == local_version and YABRIDGECTL_PATH.exists():
        print_info(f"Du hast bereits die aktuellste Version ({remote_version}) und die Installation ist intakt.")
    else:
        if not YABRIDGECTL_PATH.exists() and remote_version == local_version:
            print_info(f"Die Version ({local_version}) ist aktuell, aber die Installation ist beschädigt. Führe Reparatur durch...")
        else:
            print_info(f"Neue Version gefunden: {remote_version} (installiert: {local_version or 'keine'})")

        with tempfile.TemporaryDirectory() as tmpdir:
            tmp_path = Path(tmpdir)
            try:
                # Get artifact download URLs
                print_info("Rufe Artefakt-Liste ab...")
                response = requests.get(artifacts_url, headers=headers)
                response.raise_for_status()
                artifacts = response.json()["artifacts"]

                ctl_artifact = next((a for a in artifacts if a["name"].startswith("yabridgectl")), None)
                libs_artifact = next((a for a in artifacts if a["name"].startswith("yabridge-")), None)

                if not ctl_artifact or not libs_artifact:
                    print_error("Konnte nicht beide Artefakt-URLs finden.")
                    sys.exit(1)

                # Download and extract
                for name, artifact_url in [("ctl", ctl_artifact["archive_download_url"]), ("libs", libs_artifact["archive_download_url"])]:
                    print_info(f"Lade '{name}' herunter...")
                    # GitHub artifact URLs require following a redirect
                    dl_response = requests.get(artifact_url, headers=headers, allow_redirects=True)
                    dl_response.raise_for_status()

                    zip_path = tmp_path / f"{name}.zip"
                    zip_path.write_bytes(dl_response.content)

                    if not zipfile.is_zipfile(zip_path):
                        print_error(f"Heruntergeladene Datei für '{name}' ist kein gültiges ZIP-Archiv.")
                        sys.exit(1)

                    extract_dir = tmp_path / f"{name}_ext"
                    with zipfile.ZipFile(zip_path, 'r') as zip_ref:
                        zip_ref.extractall(extract_dir)

                    # The zip contains a tar.gz, find and extract it
                    tar_path = next(extract_dir.glob('*.tar.gz'), None)
                    if not tar_path:
                        print_error(f"Kein .tar.gz-Archiv im '{name}'-Download gefunden.")
                        sys.exit(1)

                    with tarfile.open(tar_path, "r:gz") as tar:
                        # Use a filter to strip the top-level directory
                        def strip_top_level(tarinfo):
                            tarinfo.name = '/'.join(tarinfo.name.split('/')[1:])
                            return tarinfo
                        tar.extractall(path=YABRIDGE_DIR, members=[m for m in tar.getmembers() if m.name], filter=strip_top_level)


                # Backup and install
                if YABRIDGE_DIR.exists():
                    backup_dir = HOME / ".local" / "share" / f"yabridge-backup-{datetime.datetime.now().strftime('%F-%H%M%S')}"
                    print_info(f"Sichere bestehende Installation nach {backup_dir}")
                    shutil.move(str(YABRIDGE_DIR), str(backup_dir))

                YABRIDGE_DIR.mkdir(exist_ok=True)

                # Re-run extraction to the now empty directory
                for name in ["ctl", "libs"]:
                    extract_dir = tmp_path / f"{name}_ext"
                    tar_path = next(extract_dir.glob('*.tar.gz'))
                    with tarfile.open(tar_path, "r:gz") as tar:
                         def strip_top_level(tarinfo):
                            # Ensure the member path is not empty after stripping
                            parts = tarinfo.name.split('/')[1:]
                            if not parts: return None
                            tarinfo.name = '/'.join(parts)
                            return tarinfo
                         # Filter out None values from the map
                         members_to_extract = [m for m in [strip_top_level(ti) for ti in tar.getmembers()] if m is not None and m.name]
                         tar.extractall(path=YABRIDGE_DIR, members=members_to_extract)


                # Save new version
                CONFIG_DIR.mkdir(exist_ok=True)
                VERSION_FILE.write_text(remote_version)
                print_info(f"Update auf Version {remote_version} abgeschlossen.")

            except requests.RequestException as e:
                print_error(f"Download-Fehler: {e}")
                sys.exit(1)
            except (zipfile.BadZipFile, tarfile.TarError) as e:
                print_error(f"Fehler beim Entpacken des Archivs: {e}")
                sys.exit(1)

    # --- 5. Sync ---
    print_info("Führe 'yabridgectl sync --prune' aus...")
    if not YABRIDGECTL_PATH.exists():
        print_error("yabridgectl wurde nach der Installation nicht gefunden.")
        sys.exit(1)
    try:
        subprocess.run([str(YABRIDGECTL_PATH), "sync", "--prune"], check=True)
    except (subprocess.SubprocessError, FileNotFoundError) as e:
        print_error(f"Ausführen von yabridgectl fehlgeschlagen: {e}")
        sys.exit(1)

    # --- 6. PATH Check ---
    print_info("Überprüfe und füge den Installationspfad zum PATH hinzu...")
    install_path_str = str(YABRIDGE_DIR)
    current_path = os.environ.get("PATH", "")
    if install_path_str not in current_path.split(os.pathsep):
        shell_name = os.environ.get("SHELL", "").split("/")[-1]
        config_file = None
        line_to_add = None

        if shell_name == "bash":
            config_file = HOME / ".bashrc"
            line_to_add = f'export PATH="{install_path_str}:$PATH"'
        elif shell_name == "zsh":
            config_file = HOME / ".zshrc"
            line_to_add = f'export PATH="{install_path_str}:$PATH"'
        elif shell_name == "fish":
            config_file = HOME / ".config" / "fish" / "config.fish"
            line_to_add = f"fish_add_path {install_path_str}"

        if config_file and line_to_add:
            if not config_file.exists() or line_to_add not in config_file.read_text():
                print_info(f"Füge Pfad für {shell_name} in {config_file} hinzu.")
                with config_file.open("a") as f:
                    f.write(f"\n# Added by yabridge-updater\n{line_to_add}\n")
                print_info(f"Bitte starte dein Terminal neu oder führe 'source {config_file}' aus.")
            else:
                print_info(f"Pfad ist bereits in {config_file} vorhanden.")
        else:
            print_info(f"Unbekannte Shell '{shell_name}'. Bitte füge den Pfad '{install_path_str}' manuell zu deinem PATH hinzu.")
    else:
        print_info(f"Pfad '{install_path_str}' ist bereits im PATH vorhanden.")

    print_info("Skript erfolgreich beendet.")


if __name__ == "__main__":
    # Python's requests library is required.
    try:
        import requests
    except ImportError:
        print_error("Das 'requests' Modul wird benötigt. Bitte installiere es mit 'pip install requests'.")
        sys.exit(1)
    main()
