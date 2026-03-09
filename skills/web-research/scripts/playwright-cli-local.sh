#!/usr/bin/env bash
set -euo pipefail
SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
SKILL_DIR="$(cd "$SCRIPT_DIR/.." && pwd)"
export PLAYWRIGHT_BROWSERS_PATH="$SKILL_DIR/vendor/pw-browsers"
exec "$SKILL_DIR/vendor/node_modules/.bin/playwright-cli" "$@"
