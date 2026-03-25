#!/usr/bin/env bash
set -euo pipefail

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
SKILL_DIR="$(cd "$SCRIPT_DIR/.." && pwd)"
VENDOR_DIR="$SKILL_DIR/vendor/pylib"

mkdir -p "$VENDOR_DIR"

python3 -m pip install \
  --disable-pip-version-check \
  --target "$VENDOR_DIR" \
  html2text \
  scrapling

echo "Installed fallback dependencies into $VENDOR_DIR"
