#!/usr/bin/env bash
set -euo pipefail

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
SKILL_DIR="$(cd "${SCRIPT_DIR}/.." && pwd)"
WORKSPACE_DIR="$(cd "${SKILL_DIR}/../.." && pwd)"
BASE_DIR="${WEB_BACKLINKER_BASE_DIR:-${WORKSPACE_DIR}/data/web-backlinker}"
SESSION="${BROWSER_USE_SESSION:-wb-fast}"
RETRIES="${BROWSER_USE_RETRIES:-2}"
TIMEOUT_SECONDS="${BROWSER_USE_TIMEOUT_SECONDS:-90}"
LOG_DIR="${BASE_DIR}/logs/browser-use"
GLOBAL_ENV="/home/gc/.openclaw/.env"
LOCAL_ENV="${BASE_DIR}/.env"
mkdir -p "${LOG_DIR}"

resolve_browser_use_bin() {
  if [[ -n "${WEB_BACKLINKER_BROWSER_USE_BIN:-}" && -x "${WEB_BACKLINKER_BROWSER_USE_BIN}" ]]; then
    echo "${WEB_BACKLINKER_BROWSER_USE_BIN}"
    return 0
  fi
  if command -v browser-use >/dev/null 2>&1; then
    command -v browser-use
    return 0
  fi
  if [[ -x "/home/gc/CodexOauthMangerInOpenclaw/.venv/bin/browser-use" ]]; then
    echo "/home/gc/CodexOauthMangerInOpenclaw/.venv/bin/browser-use"
    return 0
  fi
  return 1
}

BROWSER_USE_BIN="$(resolve_browser_use_bin || true)"
if [[ -z "${BROWSER_USE_BIN}" ]]; then
  echo "ERROR: browser-use binary not found. Set WEB_BACKLINKER_BROWSER_USE_BIN." >&2
  exit 127
fi
PYTHON_BIN="${BROWSER_USE_BIN%/browser-use}/python"

usage() {
  cat <<EOF
Usage:
  $(basename "$0") <browser-use args...>

Examples:
  $(basename "$0") reset
  $(basename "$0") open https://example.com
  $(basename "$0") get title
  $(basename "$0") run "Open https://example.com and return the title." --llm gemini-2.5-flash

Env loading order:
  1. /home/gc/.openclaw/.env
  2. ${BASE_DIR}/.env
EOF
}

load_env() {
  if [[ -f "${GLOBAL_ENV}" ]]; then
    set -a
    # shellcheck disable=SC1090
    source "${GLOBAL_ENV}"
    set +a
  fi
  if [[ -f "${LOCAL_ENV}" ]]; then
    set -a
    # shellcheck disable=SC1090
    source "${LOCAL_ENV}"
    set +a
  fi
}

need_llm_key() {
  local subcmd="$1"
  case "${subcmd}" in
    run|extract) return 0 ;;
    *) return 1 ;;
  esac
}

check_required_env() {
  local subcmd="$1"
  if need_llm_key "${subcmd}"; then
    if [[ -z "${GOOGLE_API_KEY:-}" && -z "${GEMINI_API_KEY:-}" && -z "${OPENAI_API_KEY:-}" && -z "${ANTHROPIC_API_KEY:-}" && -z "${BROWSER_USE_API_KEY:-}" ]]; then
      echo "ERROR: no LLM/API key visible. Put one in ${GLOBAL_ENV} or ${LOCAL_ENV}." >&2
      exit 3
    fi
  fi
}

cleanup_stale_session_files() {
  local tmpdir
  tmpdir="$(${PYTHON_BIN} - <<'PY'
import tempfile
print(tempfile.gettempdir())
PY
)"
  rm -f \
    "${tmpdir}/browser-use-${SESSION}.sock" \
    "${tmpdir}/browser-use-${SESSION}.pid" \
    "${tmpdir}/browser-use-${SESSION}.lock" \
    "${tmpdir}/browser-use-${SESSION}.meta"
}

best_effort_stop() {
  set +e
  timeout 15s "${BROWSER_USE_BIN}" --session "${SESSION}" close --all >/dev/null 2>&1
  timeout 15s "${BROWSER_USE_BIN}" --session "${SESSION}" server stop >/dev/null 2>&1
  pkill -f "browser_use.skill_cli.server --session ${SESSION}" >/dev/null 2>&1
  pkill -f "browser-use.*--session ${SESSION}" >/dev/null 2>&1
  set -e
  sleep 1
}

session_is_responsive() {
  SESSION_NAME="${SESSION}" "${PYTHON_BIN}" - <<'PY' >/dev/null 2>&1
import os
from browser_use.skill_cli.main import connect_to_server, is_server_running
session = os.environ['SESSION_NAME']
if not is_server_running(session):
    raise SystemExit(1)
sock = connect_to_server(session, timeout=0.5)
sock.close()
PY
}

command_needs_fresh_start() {
  local subcmd="$1"
  case "${subcmd}" in
    open|run|python) return 0 ;;
    *) return 1 ;;
  esac
}

command_requires_existing_session() {
  local subcmd="$1"
  case "${subcmd}" in
    click|type|input|scroll|back|screenshot|state|switch|close-tab|keys|select|eval|extract|hover|dblclick|rightclick|get|cookies|wait) return 0 ;;
    *) return 1 ;;
  esac
}

run_once() {
  local stamp log_file
  stamp="$(date +%Y%m%d-%H%M%S)"
  log_file="${LOG_DIR}/${SESSION}-${stamp}.log"
  {
    echo "[$(date -Is)] cwd=$(pwd) session=${SESSION} command=$*"
    timeout "${TIMEOUT_SECONDS}" "${BROWSER_USE_BIN}" --session "${SESSION}" "$@"
  } >>"${log_file}" 2>&1
}

print_latest_log() {
  cat "$(ls -1t "${LOG_DIR}"/${SESSION}-*.log | head -n 1)"
}

main() {
  if [[ $# -eq 0 ]]; then
    usage >&2
    exit 2
  fi
  load_env
  local subcmd="$1"
  if [[ "${subcmd}" == "reset" ]]; then
    best_effort_stop
    cleanup_stale_session_files
    echo "reset: ${SESSION}"
    exit 0
  fi

  check_required_env "${subcmd}"

  if command_requires_existing_session "${subcmd}" && ! session_is_responsive; then
    echo "ERROR: session '${SESSION}' is not healthy. Start with 'open' or 'run', or call 'reset'." >&2
    exit 4
  fi

  local attempt=1
  while (( attempt <= RETRIES )); do
    if (( attempt > 1 )); then
      echo "WARN: retrying browser-use command (attempt ${attempt}/${RETRIES})" >&2
    fi

    if command_needs_fresh_start "${subcmd}"; then
      if ! session_is_responsive; then
        best_effort_stop
        cleanup_stale_session_files
      fi
    fi

    if run_once "$@"; then
      print_latest_log
      exit 0
    fi

    local latest_log
    latest_log="$(ls -1t "${LOG_DIR}"/${SESSION}-*.log | head -n 1)"
    if grep -Eq 'Failed to start session server|ConnectionRefusedError|timed out|No response from server|BrowserStartEvent' "${latest_log}"; then
      best_effort_stop
      cleanup_stale_session_files
      attempt=$((attempt + 1))
      sleep 2
      continue
    fi

    cat "${latest_log}" >&2
    exit 1
  done

  print_latest_log >&2
  exit 1
}

main "$@"
