#!/usr/bin/env bash
set -euo pipefail

ROOT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"
cd "$ROOT_DIR"

echo "repo: $ROOT_DIR"
printf 'shell_ok\n'

echo
echo "[runtime]"
python3 --version
node --version
npm --version

echo
echo "[git]"
git rev-parse --is-inside-work-tree >/dev/null
git remote -v | sed -n '1,4p'
git ls-remote --heads origin | sed -n '1,4p'
git push --dry-run origin main

echo
echo "[python env]"
if [ ! -x ".venv/bin/python" ]; then
  echo "error: missing .venv/bin/python"
  echo "Run ./scripts/setup_local.sh first."
  exit 1
fi

./.venv/bin/python -m pytest -q \
  tests/test_temporal_analysis.py \
  tests/test_pipeline.py \
  tests/test_telegram_export.py

echo
echo "sanity_ok"
