#!/usr/bin/env bash
# Envoltorio del instalador: bash setup/setup_project.sh [--dev] [--seed] [--reset-db]
set -euo pipefail
SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
exec bash "$SCRIPT_DIR/setup_macos_linux.sh" "$@"
