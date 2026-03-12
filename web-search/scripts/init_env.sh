#!/usr/bin/env bash
set -euo pipefail

codex_home="${CODEX_HOME:-$HOME/.codex}"
skills_dir="$codex_home/skills"
web_reader_skill="$skills_dir/web-reader/SKILL.md"

ensure_curl() {
  if command -v curl >/dev/null 2>&1; then
    echo "curl is available."
  else
    echo "curl is required for Exa and Tavily requests but was not found in PATH."
    echo "Install curl or adjust PATH before using this skill."
  fi
}

report_key_status() {
  local key_name="$1"
  local provider_name="$2"
  local dashboard_url="$3"

  if [[ -n "${!key_name:-}" ]]; then
    echo "$key_name is configured. $provider_name is available."
  else
    echo "当前未配置 $key_name"
    echo "可以去 $dashboard_url 获取"
    echo "请先由 agent 询问用户是否现在提供 key。"
  fi
}

ensure_duckduckgo_search() {
  if python3 - <<'PY'
from importlib.util import find_spec
raise SystemExit(0 if find_spec("duckduckgo_search") else 1)
PY
  then
    echo "duckduckgo-search is available in python3."
  else
    echo "duckduckgo-search is not installed for python3."
    echo "Installing duckduckgo-search with python3 -m pip install --user duckduckgo-search"

    if python3 -m pip install --user --disable-pip-version-check duckduckgo-search; then
      if python3 - <<'PY'
from importlib.util import find_spec
raise SystemExit(0 if find_spec("duckduckgo_search") else 1)
PY
      then
        echo "duckduckgo-search installed successfully."
      else
        echo "duckduckgo-search install completed, but python3 still cannot import it."
        echo "Check your Python user site-packages configuration before using the DuckDuckGo fallback."
      fi
    else
      echo "Failed to install duckduckgo-search automatically."
      echo "Try again manually with: python3 -m pip install --user duckduckgo-search"
    fi
  fi
}

echo "Checking web-search environment..."

report_key_status "EXA_API_KEY" "Exa" "https://dashboard.exa.ai/api-keys"
report_key_status "TAVILY_API_KEY" "Tavily" "https://app.tavily.com/home"
echo "Search priority: Exa -> Tavily -> DuckDuckGo"
echo "For research tasks, collect from all three providers when possible."

ensure_curl
ensure_duckduckgo_search

if [[ -f "$web_reader_skill" ]]; then
  echo "web-reader skill found at $web_reader_skill"
else
  echo "web-reader skill not found. Use references/reading.md for the fallback reading flow."
fi
