#!/usr/bin/env bash
# OpenClaw adaptation: lightweight readable-path dependency check
set -euo pipefail

if command -v python3 >/dev/null 2>&1; then
  echo "python3: ok ($(python3 --version 2>/dev/null))"
else
  echo "python3: missing"
  exit 1
fi

if command -v curl >/dev/null 2>&1; then
  echo "curl: ok ($(curl --version | head -n1))"
else
  echo "curl: missing"
  exit 1
fi

if python3 - <<'PY' >/dev/null 2>&1
import importlib.util
mods = ["html2text", "scrapling"]
missing = [m for m in mods if importlib.util.find_spec(m) is None]
raise SystemExit(1 if missing else 0)
PY
then
  echo "fallback deps: ok (global env)"
else
  if [ -d "$(cd "$(dirname "$0")/.." && pwd)/vendor/pylib" ]; then
    echo "fallback deps: ok (vendor dir present)"
  else
    echo "fallback deps: missing — run: bash scripts/init_env.sh"
  fi
fi

echo "OpenClaw browser path is tool-native; no local CDP proxy bootstrap required in this fork."
