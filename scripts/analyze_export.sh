#!/usr/bin/env bash
set -euo pipefail

ROOT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"
cd "$ROOT_DIR"

if [ ! -x ".venv/bin/python" ]; then
  echo "error: local virtualenv is missing."
  echo "Run ./scripts/setup_local.sh first."
  exit 1
fi

EXPORT_PATH="${EXPORT_PATH:-$ROOT_DIR/data/telegram-export}"
OUTPUT_DIR="${OUTPUT_DIR:-$ROOT_DIR/artifacts/run-latest}"
CADENCE_DAYS="${CADENCE_DAYS:-7}"
WINDOW_DAYS="${WINDOW_DAYS:-90}"
SHORT_WINDOW_DAYS="${SHORT_WINDOW_DAYS:-30}"
WITH_LLM="${WITH_LLM:-0}"

if [ ! -e "$EXPORT_PATH" ]; then
  echo "error: export path does not exist: $EXPORT_PATH"
  echo "Put your Telegram Desktop JSON export into ./data/telegram-export"
  echo "or run with:"
  echo "  EXPORT_PATH=/absolute/path/to/export ./scripts/analyze_export.sh"
  exit 1
fi

AS_OF_DATE="${AS_OF_DATE:-$("$ROOT_DIR/.venv/bin/python" - <<'PY'
from datetime import date
print(date.today().isoformat())
PY
)}"

START_DATE="${START_DATE:-$("$ROOT_DIR/.venv/bin/python" - <<'PY'
from datetime import date, timedelta
print((date.today() - timedelta(days=91)).isoformat())
PY
)}"

CMD=(
  "$ROOT_DIR/.venv/bin/python"
  -m
  social_graph_service.cli
  analyze
  "$EXPORT_PATH"
  --output
  "$OUTPUT_DIR"
  --as-of-date
  "$AS_OF_DATE"
  --start-date
  "$START_DATE"
  --end-date
  "$AS_OF_DATE"
  --cadence-days
  "$CADENCE_DAYS"
  --window-days
  "$WINDOW_DAYS"
  --short-window-days
  "$SHORT_WINDOW_DAYS"
)

if [ "$WITH_LLM" = "1" ]; then
  CMD+=(--with-llm)
fi

PYTHONPATH=src "${CMD[@]}"

echo
echo "Artifacts written to:"
echo "  $OUTPUT_DIR"
echo
echo "Open:"
echo "  $OUTPUT_DIR/report.html"
