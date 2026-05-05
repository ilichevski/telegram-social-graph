#!/usr/bin/env bash
set -euo pipefail

ROOT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"
cd "$ROOT_DIR"

OVERVIEW_SRC="${OVERVIEW_SRC:-}"
DETAIL_SRC="${DETAIL_SRC:-}"

if [ -z "$OVERVIEW_SRC" ] || [ -z "$DETAIL_SRC" ]; then
  cat <<'EOF'
usage:
  OVERVIEW_SRC=/path/to/overview.(jpg|jpeg|png) \
  DETAIL_SRC=/path/to/detail.(jpg|jpeg|png) \
  ./scripts/update_readme_screenshots.sh

This script updates:
  docs/images/report-overview.jpg
  docs/images/report-detail.jpg

If the source is PNG, the script converts it to JPEG when `sips` (macOS) or
`magick` (ImageMagick) is available.
EOF
  exit 1
fi

OUT_DIR="$ROOT_DIR/docs/images"
mkdir -p "$OUT_DIR"

copy_or_convert() {
  local src="$1"
  local dest="$2"
  local ext
  ext="$(printf '%s' "${src##*.}" | tr '[:upper:]' '[:lower:]')"

  if [ ! -f "$src" ]; then
    echo "error: file not found: $src"
    exit 1
  fi

  case "$ext" in
    jpg|jpeg)
      cp "$src" "$dest"
      ;;
    png)
      if command -v sips >/dev/null 2>&1; then
        sips -s format jpeg "$src" --out "$dest" >/dev/null
      elif command -v magick >/dev/null 2>&1; then
        magick "$src" -quality 92 "$dest"
      else
        echo "error: cannot convert PNG to JPEG automatically."
        echo "Install ImageMagick or run on macOS with sips available."
        exit 1
      fi
      ;;
    *)
      echo "error: unsupported source extension: .$ext"
      exit 1
      ;;
  esac
}

copy_or_convert "$OVERVIEW_SRC" "$OUT_DIR/report-overview.jpg"
copy_or_convert "$DETAIL_SRC" "$OUT_DIR/report-detail.jpg"

echo "Updated screenshots:"
echo "  $OUT_DIR/report-overview.jpg"
echo "  $OUT_DIR/report-detail.jpg"
