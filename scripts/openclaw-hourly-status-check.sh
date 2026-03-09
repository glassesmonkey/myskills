#!/usr/bin/env bash
set -uo pipefail

OPENCLAW_BIN="/home/gc/.nvm/versions/node/v22.22.0/bin/openclaw"
if [[ ! -x "$OPENCLAW_BIN" ]]; then
  ALT_BIN="$(command -v openclaw 2>/dev/null || true)"
  if [[ -n "$ALT_BIN" && -x "$ALT_BIN" ]]; then
    OPENCLAW_BIN="$ALT_BIN"
  else
    cat <<'EOF'
异常
- OpenClaw CLI 不可执行：/home/gc/.nvm/versions/node/v22.22.0/bin/openclaw
- 这是巡检脚本环境问题，不能直接等同于服务故障
- 建议：检查该绝对路径是否存在，或修正脚本中的 OPENCLAW_BIN
EOF
    exit 0
  fi
fi

failures=()
TIMEOUT_BIN="$(command -v timeout 2>/dev/null || true)"

add_failure() {
  failures+=("$1")
}

run_capture() {
  local __var_name="$1"
  shift
  local output rc
  if [[ -n "$TIMEOUT_BIN" ]]; then
    output="$($TIMEOUT_BIN 15s "$@" 2>&1)"
    rc=$?
  else
    output="$($@ 2>&1)"
    rc=$?
  fi
  printf -v "$__var_name" '%s' "$output"
  return $rc
}

trim_line() {
  printf '%s' "$1" | tr '\n' ' ' | sed 's/[[:space:]]\+/ /g' | cut -c1-220
}

# 1) gateway status
if ! run_capture gateway_out "$OPENCLAW_BIN" gateway status; then
  add_failure "gateway status 失败/超时：$(trim_line "$gateway_out")"
else
  grep -q "Runtime: running" <<<"$gateway_out" || add_failure "gateway 运行态异常：未看到 Runtime: running"
  grep -q "RPC probe: ok" <<<"$gateway_out" || add_failure "gateway 探测异常：未看到 RPC probe: ok"
fi

# 2) health --json
if ! run_capture health_out "$OPENCLAW_BIN" health --json; then
  add_failure "health --json 失败/超时：$(trim_line "$health_out")"
else
  grep -Eq '"ok"[[:space:]]*:[[:space:]]*true' <<<"$health_out" || add_failure "health 检查异常：ok != true"
fi

# 3) cron status
if ! run_capture cron_out "$OPENCLAW_BIN" cron status; then
  add_failure "cron status 失败/超时：$(trim_line "$cron_out")"
else
  grep -Eq '"enabled"[[:space:]]*:[[:space:]]*true' <<<"$cron_out" || add_failure "cron scheduler 异常：enabled != true"
fi

# 4) update status（只验证命令能跑；有更新不算异常）
if ! run_capture update_out "$OPENCLAW_BIN" update status; then
  add_failure "update status 失败/超时：$(trim_line "$update_out")"
fi

if [[ ${#failures[@]} -eq 0 ]]; then
  echo "NO_REPLY"
  exit 0
fi

echo "异常"
for item in "${failures[@]}"; do
  echo "- $item"
done
echo "- 建议：优先执行 $OPENCLAW_BIN gateway status 与 $OPENCLAW_BIN health --json 复核"
