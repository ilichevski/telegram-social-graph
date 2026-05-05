#!/usr/bin/env bash
set -euo pipefail

ROOT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"
cd "$ROOT_DIR"

RUN_DIR="${RUN_DIR:-$ROOT_DIR/artifacts/run-latest}"
PORT="${PORT:-8765}"
BIND="${BIND:-127.0.0.1}"

if [ ! -d "$RUN_DIR" ]; then
  echo "error: run directory does not exist: $RUN_DIR"
  echo "Set RUN_DIR=/absolute/path/to/run or create artifacts with ./scripts/analyze_export.sh"
  exit 1
fi

if [ ! -f "$RUN_DIR/report.html" ]; then
  echo "error: missing report.html in $RUN_DIR"
  exit 1
fi

BASE_DIR="$(cd "$RUN_DIR/.." && pwd)"
RUN_NAME="$(basename "$RUN_DIR")"

echo "Serving: $BASE_DIR"
echo "Report URL: http://$BIND:$PORT/$RUN_NAME/report.html"
echo "Press Ctrl+C to stop."

cd "$BASE_DIR"
exec python3 -m http.server "$PORT" --bind "$BIND"
