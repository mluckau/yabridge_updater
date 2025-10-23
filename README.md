# Yabridge Updater

Ein Kommandozeilen-Tool zum einfachen Herunterladen, Installieren und Verwalten von Entwickler-Builds von [yabridge](https://github.com/robbert-vdh/yabridge).

---

A command-line tool to easily download, install, and manage development builds of [yabridge](https://github.com/robbert-vdh/yabridge).

---

## Inhaltsverzeichnis / Table of Contents

- [Yabridge Updater](#yabridge-updater)
  - [Inhaltsverzeichnis / Table of Contents](#inhaltsverzeichnis--table-of-contents)
  - [🇩🇪 Deutsche Dokumentation](#-deutsche-dokumentation)
    - [Features](#features)
    - [Voraussetzungen](#voraussetzungen)
    - [Installation](#installation)
    - [Benutzung (Befehle)](#benutzung-befehle)
    - [GitHub Personal Access Token (PAT)](#github-personal-access-token-pat)
    - [Deinstallation](#deinstallation)
  - [🇬🇧 English Documentation](#-english-documentation)
    - [Features](#features-1)
    - [Prerequisites](#prerequisites)
    - [Installation](#installation-1)
    - [Usage (Commands)](#usage-commands)
    - [GitHub Personal Access Token (PAT)](#github-personal-access-token-pat-1)
    - [Uninstallation](#uninstallation)

---

## 🇩🇪 Deutsche Dokumentation

### Features

*   **Automatisierte Installation**: Ein einziges Skript kümmert sich um alle Abhängigkeiten auf den gängigsten Linux-Distributionen (Debian/Ubuntu, Fedora, Arch, openSUSE).
*   **Update-Prüfung**: Prüft automatisch, ob eine neue Version im aktuell installierten Branch verfügbar ist.
*   **Interaktive Branch-Auswahl**: Ermöglicht die einfache Auswahl und Installation eines beliebigen Entwickler-Branches.
*   **Sichere Token-Speicherung**: Speichert dein GitHub PAT sicher im System-Schlüsselbund (`secret-tool`) oder als verschlüsselte Datei (`openssl`), wenn kein Schlüsselbund verfügbar ist.
*   **Backup & Restore**: Erstellt automatisch Backups vor jedem Update und ermöglicht die Wiederherstellung einer früheren Version.
*   **Aufräumfunktion**: Löscht alte Backups, um Speicherplatz freizugeben.
*   **PATH-Management**: Hilft dir, den `yabridge`-Pfad zu deiner Shell-Konfiguration hinzuzufügen, damit `yabridgectl` überall verfügbar ist.

### Voraussetzungen

*   Eine funktionierende Internetverbindung.
*   `git`, um dieses Repository zu klonen.
*   `sudo`-Rechte für die Installation.

Das Installationsskript kümmert sich um den Rest, einschließlich `python3`, `wine`, `openssl` etc.

### Installation

1.  **Repository klonen:**
    ```bash
    git clone https://github.com/mluckau/yabridge_updater.git
    cd yabridge-updater
    ```

2.  **Installationsskript ausführen:**
    Das Skript installiert den Updater und führt ihn anschließend zum ersten Mal aus, um `yabridge` selbst zu installieren.

    *   **Standard-Installation** (installiert `yabridge` nach `~/.local/share/yabridge`):
        ```bash
        sudo ./install.sh
        ```

    *   **Installation in einen benutzerdefinierten Pfad**:
        ```bash
        sudo ./install.sh /dein/gewuenschter/pfad/fuer/yabridge
        ```

3.  **Anweisungen befolgen:**
    Das Skript wird dich nach deinem GitHub PAT fragen und die Installation von `yabridge` abschließen.

### Benutzung (Befehle)

Nach der Installation kannst du `yabridge-updater` von überall im Terminal aufrufen.

| Befehl | Beschreibung |
|---|---|
| `yabridge-updater` | Standardaktion: Prüft auf Updates für den installierten Branch und installiert sie bei Bedarf. Führt bei der Erstinstallation den interaktiven Modus aus. |
| `yabridge-updater update` | Identisch zur Standardaktion. |
| `yabridge-updater update --interactive` | Erzwingt die interaktive Auswahl eines Branches, auch wenn bereits eine Version installiert ist. |
| `yabridge-updater status` | Zeigt den Installationspfad, den Branch und die Versions-ID der aktuellen `yabridge`-Installation an. |
| `yabridge-updater restore` | Listet alle verfügbaren Backups auf und ermöglicht die Wiederherstellung einer ausgewählten Version. |
| `yabridge-updater prune-backups [N]` | Löscht alle bis auf die `N` neuesten Backups (Standard: 5). |
| `yabridge-updater token --clear` | Löscht den gespeicherten GitHub-Token aus dem Schlüsselbund und/oder der Konfigurationsdatei. |
| `yabridge-updater --install-path <pfad>` | (Nur bei Erstinstallation) Gibt einen benutzerdefinierten Installationspfad für `yabridge` an. |

### GitHub Personal Access Token (PAT)

**Warum wird ein Token benötigt?**
Um Artefakte (die kompilierten Programmdateien) von GitHub Actions herunterladen zu können, ist eine Authentifizierung bei der GitHub-API erforderlich.

**Wie erstelle ich ein Token?**
1.  Gehe zu github.com/settings/tokens.
2.  Klicke auf "Generate new token" -> "Generate new token (classic)".
3.  Gib einen Namen ein (z.B. "Yabridge Updater").
4.  Setze ein Ablaufdatum.
5.  Wähle den Scope `repo` aus.
6.  Klicke auf "Generate token" und kopiere das angezeigte Token.

Das Skript wird dich bei der ersten Ausführung nach diesem Token fragen.

### Deinstallation

1.  Navigiere in das geklonte Verzeichnis:
    ```bash
    cd yabridge-updater
    ```

2.  Führe das Deinstallations-Skript aus:
    ```bash
    sudo ./uninstall.sh
    ```
    Das Skript wird dich fragen, ob auch die Konfigurationsdateien und die `yabridge`-Installation selbst gelöscht werden sollen.

3.  **Manuelle Bereinigung:**
    Entferne die Zeile `export PATH="..."` oder `fish_add_path ...`, die vom Updater zu deiner Shell-Konfigurationsdatei (`~/.bashrc`, `~/.zshrc`, etc.) hinzugefügt wurde.

---

## 🇬🇧 English Documentation

### Features

*   **Automated Installation**: A single script handles all dependencies on major Linux distributions (Debian/Ubuntu, Fedora, Arch, openSUSE).
*   **Update Check**: Automatically checks if a new version is available for the currently installed branch.
*   **Interactive Branch Selection**: Allows for easy selection and installation of any development branch.
*   **Secure Token Storage**: Securely stores your GitHub PAT in the system keyring (`secret-tool`) or as an encrypted file (`openssl`) if no keyring is available.
*   **Backup & Restore**: Automatically creates backups before each update and allows restoring a previous version.
*   **Pruning**: Deletes old backups to free up disk space.
*   **PATH Management**: Helps you add the `yabridge` path to your shell configuration, making `yabridgectl` available everywhere.

### Prerequisites

*   A working internet connection.
*   `git` to clone this repository.
*   `sudo` privileges for the installation.

The installation script takes care of the rest, including `python3`, `wine`, `openssl`, etc.

### Installation

1.  **Clone the repository:**
    ```bash
    git clone https://github.com/mluckau/yabridge_updater.git
    cd yabridge-updater
    ```

2.  **Run the installation script:**
    The script will install the updater and then run it for the first time to install `yabridge` itself.

    *   **Default Installation** (installs `yabridge` to `~/.local/share/yabridge`):
        ```bash
        sudo ./install.sh
        ```

    *   **Installation to a custom path**:
        ```bash
        sudo ./install.sh /your/desired/path/for/yabridge
        ```

3.  **Follow the instructions:**
    The script will ask for your GitHub PAT and complete the `yabridge` installation.

### Usage (Commands)

After installation, you can call `yabridge-updater` from anywhere in your terminal.

| Command | Description |
|---|---|
| `yabridge-updater` | Default action: Checks for updates on the installed branch and installs them if available. Runs interactive mode on first install. |
| `yabridge-updater update` | Identical to the default action. |
| `yabridge-updater update --interactive` | Forces interactive branch selection, even if a version is already installed. |
| `yabridge-updater status` | Displays the installation path, branch, and version ID of the current `yabridge` installation. |
| `yabridge-updater restore` | Lists all available backups and allows restoring a selected version. |
| `yabridge-updater prune-backups [N]` | Deletes all but the `N` most recent backups (default: 5). |
| `yabridge-updater token --clear` | Deletes the stored GitHub token from the keyring and/or configuration file. |
| `yabridge-updater --install-path <path>` | (On first run only) Specifies a custom installation path for `yabridge`. |

### GitHub Personal Access Token (PAT)

**Why is a token needed?**
To download artifacts (the compiled program files) from GitHub Actions, authentication with the GitHub API is required.

**How do I create a token?**
1.  Go to github.com/settings/tokens.
2.  Click "Generate new token" -> "Generate new token (classic)".
3.  Enter a name (e.g., "Yabridge Updater").
4.  Set an expiration date.
5.  Select the `repo` scope.
6.  Click "Generate token" and copy the displayed token.

The script will ask you for this token on its first run.

### Uninstallation

1.  Navigate to the cloned directory:
    ```bash
    cd yabridge-updater
    ```

2.  Run the uninstallation script:
    ```bash
    sudo ./uninstall.sh
    ```
    The script will ask if you also want to delete the configuration files and the `yabridge` installation itself.

3.  **Manual Cleanup:**
    Remove the `export PATH="..."` or `fish_add_path ...` line that was added by the updater to your shell configuration file (`~/.bashrc`, `~/.zshrc`, etc.).