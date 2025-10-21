# Project: yabridge_updater

## Project Overview
This project contains a bash script named `yabridge-update-dev`. Its purpose is to download and install the latest developer version of `yabridge` (libs and ctl) from the "new-wine10-embedding" branch of the `robbert-vdh/yabridge` GitHub repository. It uses the GitHub API and `jq` for parsing. It also handles GitHub Personal Access Token (PAT) management, including storing it securely in the system keyring or an encrypted file.

## Building and Running
The script itself is the main executable. It does not require a separate build step.

**To run the script:**
```bash
./yabridge-update-dev
```

**To update or clear the GitHub token:**
```bash
./yabridge-update-dev --update-token
```

## Development Conventions
*   **Language:** Bash scripting.
*   **Dependencies:** Relies on `jq` and `curl` for API interactions. Uses `secret-tool` or `openssl` for secure token storage.
*   **Installation Path:** Installs `yabridge` and `yabridgectl` into `$HOME/.local/share/yabridge`.
*   **Backup:** Performs backups of existing installations before updating.
*   **Post-Installation:** Runs `yabridgectl sync --prune` after a successful installation.
