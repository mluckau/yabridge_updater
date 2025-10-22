# Project: yabridge_updater (Python Version)

## Project Overview
This project is a sophisticated Python script, `yabridge_updater`, designed to manage development versions of `yabridge`. It evolved from a simple bash script into a feature-rich command-line utility. Its primary purpose is to download, install, and update `yabridge` from the artifacts of GitHub Actions workflows.

## Current State & Features

The script is a single executable file, `yabridge_updater`, and uses a configuration directory at `~/.config/yabridge-updater/`.

### Command-Line Interface (CLI)

The script uses a modern sub-command structure:

-   `./yabridge_updater [update]`: The default command. Automatically checks for updates for the currently installed branch and prompts for installation if a new version is found.
    -   `--interactive`: A flag for the `update` command to force the interactive branch selection mode.
-   `./yabridge_updater status`: Displays the current installation path, the installed branch, and the version SHA.
-   `./yabridge_updater restore`: Starts an interactive process to restore a previous version from available backups.
-   `./yabridge_updater prune-backups [N]`: A standalone command to delete old backups, keeping the last `N` (default: 5).
-   `./yabridge_updater token --clear`: A command to clear any stored GitHub PAT from the system keyring or encrypted file.

### Core Logic & Functionality

-   **Automatic Update Check:** The default behavior is to intelligently check for updates for the specific branch that was last installed.
-   **Self-Contained Versioning:** Each installation contains a `.version` JSON file, storing the commit SHA and the branch name, making backups and restores robust.
-   **Secure Token Handling:** Securely manages GitHub Personal Access Tokens (PAT) with a preference for the system's Secret Service (`secret-tool`) and a fallback to an `openssl`-encrypted file.
-   **Backup & Restore:** Automatically creates timestamped backups of the previous installation before updating. The `restore` command allows for easy rollbacks.
-   **Enhanced UX:** Features a polished command-line interface with colored output, headers, status symbols (✓, ✗), and a progress bar for downloads.
-   **Robustness:** Includes specific error handling for network, file, and subprocess errors, as well as a warning for GitHub API rate-limiting.

## Next Steps
The script is functionally complete and polished. Future work could involve adding new commands or refining existing ones based on user feedback. The current structure is modular and easily extensible.