#!/usr/bin/env bash
set -euo pipefail

ROOT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"
cd "$ROOT_DIR"

PYTHON_BIN="${PYTHON_BIN:-python3}"

if ! command -v "$PYTHON_BIN" >/dev/null 2>&1; then
  echo "error: python3 not found"
  exit 1
fi

if [ ! -d ".venv" ]; then
  "$PYTHON_BIN" -m venv .venv
fi

.venv/bin/python -m pip install --upgrade pip
.venv/bin/python -m pip install -e ".[dev]"

echo
echo "Local environment is ready."
echo "Next steps:"
echo "  1. Put your Telegram Desktop JSON export in ./data/telegram-export"
echo "  2. Optionally run ./scripts/pull_models.sh"
echo "  3. Run ./scripts/analyze_export.sh"
