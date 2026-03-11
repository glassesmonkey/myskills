#!/usr/bin/env bash
set -euo pipefail

codex_home="${CODEX_HOME:-$HOME/.codex}"
skills_dir="$codex_home/skills"
web_reader_skill="$skills_dir/web-reader/SKILL.md"

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

if [[ -n "${TAVILY_API_KEY:-}" ]]; then
  echo "TAVILY_API_KEY is configured. Tavily will be used first."
else
  echo "当前未配置 TAVILY_API_KEY"
  echo "可以去 https://app.tavily.com/home 获取"
  echo "请先由 agent 询问用户是否现在提供 key。"
  echo "如果用户跳过，再回退到 DuckDuckGo。"
fi

ensure_duckduckgo_search

if [[ -f "$web_reader_skill" ]]; then
  echo "web-reader skill found at $web_reader_skill"
else
  echo "web-reader skill not found. Use references/reading.md for the fallback reading flow."
fi
