#!/usr/bin/env bash
set -euo pipefail

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
SAFE_BIN="${SCRIPT_DIR}/browser_use_safe.sh"
RUNS="${1:-5}"
MODE="${2:-direct}"
SUCCESS=0
FAIL=0
TOTAL_DURATION=0

run_direct() {
  local start end out title_line
  start=$(date +%s)
  "${SAFE_BIN}" reset >/dev/null
  out="$(${SAFE_BIN} open https://example.com && ${SAFE_BIN} get title && ${SAFE_BIN} close 2>&1)"
  end=$(date +%s)
  title_line=$(printf '%s\n' "$out" | grep 'title:' | tail -n 1 || true)
  if [[ "${title_line}" != *"Example Domain"* ]]; then
    printf '%s\n' "$out"
    echo "$((end-start))"
    return 1
  fi
  echo "$out"
  echo "$((end-start))"
}

run_agent() {
  local start end out
  start=$(date +%s)
  "${SAFE_BIN}" reset >/dev/null
  out="$(${SAFE_BIN} run "Open https://example.com and return the page title only." --llm gemini-2.5-flash 2>&1)"
  end=$(date +%s)
  if [[ "$out" != *"Example Domain"* ]]; then
    printf '%s\n' "$out"
    echo "$((end-start))"
    return 1
  fi
  echo "$out"
  echo "$((end-start))"
}

for i in $(seq 1 "$RUNS"); do
  echo "===== smoke run ${i}/${RUNS} mode=${MODE} ====="
  set +e
  if [[ "${MODE}" == "agent" ]]; then
    result=$(run_agent)
    code=$?
  else
    result=$(run_direct)
    code=$?
  fi
  set -e

  duration=$(printf '%s\n' "$result" | tail -n 1)
  body=$(printf '%s\n' "$result" | sed '$d')
  echo "$body"
  echo "DURATION=${duration}s EXIT=${code}"
  TOTAL_DURATION=$((TOTAL_DURATION + duration))

  if [[ $code -eq 0 ]]; then
    SUCCESS=$((SUCCESS + 1))
  else
    FAIL=$((FAIL + 1))
  fi
  echo
  sleep 2
done

echo "===== summary ====="
echo "success=${SUCCESS} fail=${FAIL} avg_duration=$(( TOTAL_DURATION / RUNS ))s total_duration=${TOTAL_DURATION}s mode=${MODE}"
if [[ $FAIL -gt 0 ]]; then
  exit 1
fi
