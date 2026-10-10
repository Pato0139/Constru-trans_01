#!/usr/bin/env bash

set -euo pipefail
cd "$(dirname "$0")"
REPO_ROOT="$(pwd)"
TEMP_DIR="$REPO_ROOT/temp_neon_repo"
cleanup_temp() {
    if [ -d "$TEMP_DIR" ]; then
        rm -rf "$TEMP_DIR" 2>/dev/null || true
    fi
}
trap cleanup_temp EXIT INT TERM HUP
bash setup/setup_macos_linux.sh
