# Yabridge Updater

Ein Kommandozeilen-Tool zum einfachen Herunterladen, Installieren und Verwalten von Entwicklerversionen von [yabridge](https://github.com/robbert-vdh/yabridge) direkt von GitHub Actions.

This is a command-line tool to easily download, install, and manage development versions of [yabridge](https://github.com/robbert-vdh/yabridge) directly from GitHub Actions.

---

<details>
<summary><strong>English Documentation</strong></summary>

## Features

- **Update Management**: Automatically checks if a newer version of your currently installed yabridge branch is available and prompts for installation.
- **Interactive Installation**: If no version is installed or forced via `--interactive`, it presents a list of all available branches with successful builds to choose from.
- **Secure Token Management**: Securely stores your GitHub Personal Access Token (PAT) using the system's keyring (`secret-tool`) or an `openssl`-encrypted file as a fallback.
- **Automatic Backups**: Creates a backup of your current yabridge installation before every update or restore.
- **Backup Management**:
    - `restore`: Restore a previous version from a list of available backups.
    - `prune-backups`: Clean up old backups to save space.
- **Plugin Sync**: The `sync` command allows you to manually run `yabridgectl sync --prune` without performing a full update.
- **Self-Update**: The script can update itself to the latest version from its own GitHub repository using the `self-update` command.
- **PATH Management**: Automatically detects if the installation directory is in your shell's `PATH` and offers to add it to your `.bashrc`, `.zshrc`, or `config.fish`.
- **Status Overview**: The `status` command shows the currently installed version, branch, and installation path.
- **Multi-language**: The user interface is available in both English and German and autodetects the system language.

## Installation

You can install the updater with a single command. It will download the repository, install system dependencies, and place the `yabridge-updater` script in `/usr/local/bin`.

```bash
curl -L https://raw.githubusercontent.com/mluckau/yabridge_updater/main/install.sh | sudo bash
```

The installer automatically detects your distribution (Debian/Ubuntu, Fedora, Arch, openSUSE) and installs the following dependencies:
`python3`, `python3-pip`, `git`, `openssl`, `libsecret-tools`, `python3-requests`, `wine`.

### Custom Installation Path for yabridge

If you want to install `yabridge` itself to a custom location (e.g., on another drive), you can pass the path to the installer. This path will be saved and used for all future operations.

```bash
curl -L https://raw.githubusercontent.com/mluckau/yabridge_updater/main/install.sh | sudo bash -s -- /path/to/your/custom/yabridge/folder
```

## Usage

Simply run the command `yabridge-updater` in your terminal.

```bash
yabridge-updater [command] [options]
```

### First Run

On the first run, the script will ask for a **GitHub Personal Access Token (PAT)**. This is required to access the GitHub Actions API to download build artifacts.

1.  Go to github.com/settings/tokens to generate a new token.
2.  For public repositories, the `public_repo` scope is sufficient.
3.  The script will offer to save the token securely in your system's keyring for future use.

### Commands

- **`update` (default)**: Checks for an update for the currently installed branch. If no version is installed, it starts the interactive mode.
  - `--interactive`: Forces the interactive mode to select and install a different branch.
- **`sync`**: Manually runs `yabridgectl sync --prune` to synchronize your VST plugins.
- **`status`**: Displays information about the current installation (path, version, branch).
- **`restore`**: Shows a list of available backups and allows you to restore one.
- **`prune-backups [keep]`**: Deletes old backups, keeping the specified number of recent backups (default: 5).
- **`self-update`**: Checks for a new version of the `yabridge-updater` script itself and performs an update if available.
- **`token --clear`**: Deletes the stored GitHub token from the keyring and/or the encrypted file.

### Global Options

- **`--install-path /path/to/yabridge`**: Overrides the default or saved installation path for a single run.

## Uninstallation

To completely remove the updater and all related data, run the `uninstall.sh` script from the repository.

```bash
curl -L https://raw.githubusercontent.com/mluckau/yabridge_updater/main/uninstall.sh | sudo bash
```

The script will:
1.  Remove the `yabridge-updater` command from `/usr/local/bin`.
2.  Automatically remove the `PATH` entry from your shell configuration file.
3.  Ask you interactively if you want to delete the configuration directory (`~/.config/yabridge-updater`).
4.  Ask you interactively if you want to delete the yabridge installation and all backups.

</details>

<details open>
<summary><strong>Deutsche Dokumentation</strong></summary>

## Features

- **Update-Management**: Prüft automatisch, ob eine neuere Version des aktuell installierten yabridge-Branches verfügbar ist, und fragt nach der Installation.
- **Interaktive Installation**: Wenn keine Version installiert ist oder `--interactive` erzwungen wird, zeigt das Skript eine Liste aller verfügbaren Branches mit erfolgreichen Builds zur Auswahl an.
- **Sicheres Token-Management**: Speichert dein GitHub Personal Access Token (PAT) sicher im System-Schlüsselbund (`secret-tool`) oder als Fallback in einer mit `openssl` verschlüsselten Datei.
- **Automatische Backups**: Erstellt vor jedem Update oder jeder Wiederherstellung ein Backup deiner aktuellen yabridge-Installation.
- **Backup-Verwaltung**:
    - `restore`: Stellt eine frühere Version aus einer Liste verfügbarer Backups wieder her.
    - `prune-backups`: Räumt alte Backups auf, um Speicherplatz freizugeben.
- **Plugin-Synchronisation**: Der `sync`-Befehl ermöglicht es, `yabridgectl sync --prune` manuell auszuführen, ohne ein komplettes Update durchzuführen.
- **Self-Update**: Das Skript kann sich mit dem Befehl `self-update` selbst auf die neueste Version aus seinem GitHub-Repository aktualisieren.
- **PATH-Management**: Erkennt automatisch, ob das Installationsverzeichnis im `PATH` deiner Shell enthalten ist, und bietet an, es zu deiner `.bashrc`, `.zshrc` oder `config.fish` hinzuzufügen.
- **Status-Übersicht**: Der `status`-Befehl zeigt die aktuell installierte Version, den Branch und den Installationspfad an.
- **Mehrsprachigkeit**: Die Benutzeroberfläche ist auf Deutsch und Englisch verfügbar und erkennt automatisch die Systemsprache.

## Installation

Du kannst den Updater mit einem einzigen Befehl installieren. Er lädt das Repository herunter, installiert Systemabhängigkeiten und legt das Skript `yabridge-updater` in `/usr/local/bin` ab.

```bash
curl -L https://raw.githubusercontent.com/mluckau/yabridge_updater/main/install.sh | sudo bash
```

Der Installer erkennt automatisch deine Distribution (Debian/Ubuntu, Fedora, Arch, openSUSE) und installiert die folgenden Abhängigkeiten:
`python3`, `python3-pip`, `git`, `openssl`, `libsecret-tools`, `python3-requests`, `wine`.

### Eigener Installationspfad für yabridge

Wenn du `yabridge` selbst an einem benutzerdefinierten Ort installieren möchtest (z.B. auf einem anderen Laufwerk), kannst du den Pfad an den Installer übergeben. Dieser Pfad wird gespeichert und für alle zukünftigen Operationen verwendet.

```bash
curl -L https://raw.githubusercontent.com/mluckau/yabridge_updater/main/install.sh | sudo bash -s -- /pfad/zu/deinem/yabridge/ordner
```

## Benutzung

Führe einfach den Befehl `yabridge-updater` in deinem Terminal aus.

```bash
yabridge-updater [Befehl] [Optionen]
```

### Erster Start

Beim ersten Start fragt das Skript nach einem **GitHub Personal Access Token (PAT)**. Dieses wird benötigt, um auf die GitHub Actions API zuzugreifen und Build-Artefakte herunterzuladen.

1.  Gehe zu github.com/settings/tokens, um ein neues Token zu erstellen.
2.  Für öffentliche Repositories ist der Geltungsbereich (Scope) `public_repo` ausreichend.
3.  Das Skript bietet an, das Token für die zukünftige Verwendung sicher in deinem System-Schlüsselbund zu speichern.

### Befehle

- **`update` (Standard)**: Sucht nach einem Update für den aktuell installierten Branch. Wenn keine Version installiert ist, startet der interaktive Modus.
  - `--interactive`: Erzwingt den interaktiven Modus, um einen anderen Branch auszuwählen und zu installieren.
- **`sync`**: Führt `yabridgectl sync --prune` manuell aus, um deine VST-Plugins zu synchronisieren.
- **`status`**: Zeigt Informationen über die aktuelle Installation an (Pfad, Version, Branch).
- **`restore`**: Zeigt eine Liste der verfügbaren Backups an und ermöglicht die Wiederherstellung eines Backups.
- **`prune-backups [keep]`**: Löscht alte Backups und behält die angegebene Anzahl der neuesten Backups (Standard: 5).
- **`self-update`**: Sucht nach einer neuen Version des `yabridge-updater`-Skripts selbst und führt bei Verfügbarkeit ein Update durch.
- **`token --clear`**: Löscht das gespeicherte GitHub-Token aus dem Schlüsselbund und/oder der verschlüsselten Datei.

### Globale Optionen

- **`--install-path /pfad/zu/yabridge`**: Überschreibt den standardmäßigen oder gespeicherten Installationspfad für einen einzelnen Durchlauf.

## Deinstallation

Um den Updater und alle zugehörigen Daten vollständig zu entfernen, führe das `uninstall.sh`-Skript aus dem Repository aus.

```bash
curl -L https://raw.githubusercontent.com/mluckau/yabridge_updater/main/uninstall.sh | sudo bash
```

Das Skript wird:
1.  Den Befehl `yabridge-updater` aus `/usr/local/bin` entfernen.
2.  Den `PATH`-Eintrag automatisch aus deiner Shell-Konfigurationsdatei entfernen.
3.  Dich interaktiv fragen, ob das Konfigurationsverzeichnis (`~/.config/yabridge-updater`) gelöscht werden soll.
4.  Dich interaktiv fragen, ob die yabridge-Installation und alle Backups gelöscht werden sollen.

</details>