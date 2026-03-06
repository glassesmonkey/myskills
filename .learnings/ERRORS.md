# Errors Log

Command failures, exceptions, and unexpected behaviors.

---

## [ERR-20260227-001] memory_search

**Logged**: 2026-02-27T10:14:27+08:00
**Priority**: high
**Status**: pending
**Area**: config

### Summary
memory_search failed because embeddings provider returned invalid API key (401).

### Error
```
openai embeddings failed: 401 invalid_api_key
Incorrect API key provided
```

### Context
- Operation: `memory_search` before answering memory-related question
- Result: tool unavailable (`disabled=true`, `unavailable=true`)

### Suggested Fix
- Verify embedding provider API key in OpenClaw config/environment.
- Ensure embeddings provider and model are valid and billable.
- Retry `memory_search` after updating config and restarting gateway if needed.

### Metadata
- Reproducible: yes
- Related Files: memory/hook-message-state.json

---
## [ERR-20260303-001] clawhub-install

**Logged**: 2026-03-03T23:28:49+08:00
**Priority**: medium
**Status**: pending
**Area**: config

### Summary
Failed to install Notion skill due to ClawHub rate limit.

### Error
```
npx clawhub install notion
✖ Rate limit exceeded
Error: Rate limit exceeded
```

### Context
- User requested enabling Notion skill.
- `clawdhub` binary not installed locally; used `npx clawhub` instead.
- Search succeeded; install blocked by rate limiting.

### Suggested Fix
Retry install later after rate limit window resets.

### Metadata
- Reproducible: unknown
- Related Files: .learnings/ERRORS.md
- See Also: none

---
## [ERR-20260303-002] message-react-telegram

**Logged**: 2026-03-03T23:50:00+08:00
**Priority**: medium
**Status**: pending
**Area**: config

### Summary
Failed to add Telegram reaction via  tool even when using  and message id.

### Error
targettochannelId

### Context
- User asked to test immediate "processing" reaction in Telegram group.
- Attempted multiple  calls with  and messageId.
- Tool still returned the same validation error, likely due adapter/schema mismatch.

### Suggested Fix
- Check message tool input schema for react on Telegram and required minimal fields.
- Verify whether empty /default injected fields trigger false validation.
- Retry with minimal payload once tool behavior is confirmed.

### Metadata
- Reproducible: yes
- Related Files: .learnings/ERRORS.md
- See Also: none

---
## [ERR-20260303-002] message-react-telegram

**Logged**: 2026-03-03T23:49:40+08:00
**Priority**: medium
**Status**: pending
**Area**: config

### Summary
Failed to add Telegram reaction via `message` tool while testing "processing" emoji acknowledgement.

### Error
```
Use `target` instead of `to`/`channelId`.
```

### Context
- User asked to test immediate reaction in Telegram group.
- Multiple `message(action=react)` attempts were made with `target` + `messageId`.
- Same validation error repeated, indicating tool-side/schema mismatch in this session context.

### Suggested Fix
- Recheck message tool react payload requirements for Telegram.
- Verify whether same-chat constraints require native reply-only path.
- Retest with minimal payload once tool behavior is confirmed.

### Metadata
- Reproducible: yes
- Related Files: .learnings/ERRORS.md
- See Also: none

---
## [ERR-20260303-003] telegram-react-still-fails-after-update

**Logged**: 2026-03-03T23:59:40+08:00
**Priority**: high
**Status**: pending
**Area**: config

### Summary
Telegram reaction via `message` tool still fails after upgrading OpenClaw from 2026.3.1 to 2026.3.2 and restarting gateway.

### Error
```
Use `target` instead of `to`/`channelId`.
```

### Context
- Upgrade completed successfully and gateway restarted.
- Re-test on message 429 still fails with same validation error.
- Indicates payload/schema mismatch is not fixed by version bump alone.

### Suggested Fix
- Inspect message tool adapter validation for react path on Telegram.
- Try minimal payload through official examples/docs if available.
- If reproducible, open bug report with logs and exact payload.

### Metadata
- Reproducible: yes
- Related Files: .learnings/ERRORS.md
- See Also: ERR-20260303-002

---
## [ERR-20260304-001] notion-create

**Logged**: 2026-03-04T00:06:52+08:00
**Priority**: medium
**Status**: pending
**Area**: config

### Summary
Notion batch page creation failed because target parent block/page is archived or inaccessible.

### Error
```
Can't edit block that is archived. You must unarchive the block before editing.
```

### Context
- User asked to create multiple notes for visibility testing.
- API search returned zero results for shared pages.
- Direct create under previous parent page ID also failed with archived-block error.

### Suggested Fix
Use a non-archived page/database in the correct workspace and share it with the integration, then create pages under that parent.

### Metadata
- Reproducible: yes
- Related Files: notion-output/latest-batch.md, .learnings/ERRORS.md
- See Also: ERR-20260303-001

---

## [ERR-20260304-001] codex-launch-flag-conflict

**Logged**: 2026-03-04T10:08:30+08:00
**Priority**: medium
**Status**: resolved
**Area**: workflow

### Summary
tmux 中启动 Codex 时触发参数冲突：`--dangerously-bypass-approvals-and-sandbox` 与 `--full-auto` 不能同时使用。

### Error
```
error: the argument '--dangerously-bypass-approvals-and-sandbox' cannot be used with '--full-auto'
```

### Context
- 在 `codex-build`、`codex-qa` session 使用 `codex --full-auto` 启动时出现。
- 本机 Codex 默认配置里包含 yolo/危险执行相关参数，导致与 `--full-auto` 冲突。

### Suggested Fix
- 启动时避免叠加 `--full-auto`；改用 `codex '<prompt>'`（沿用默认配置）或显式清理冲突配置。
- 已在同一轮执行中恢复：重发命令后两个 Codex session 均正常进入运行态。

### Resolution
- **Resolved**: 2026-03-04T10:08:30+08:00
- **Notes**: 已恢复 codex-build / codex-qa 运行，后续 watchdog 继续监控并自动重启。

### Metadata
- Reproducible: yes
- Related Files: .learnings/ERRORS.md
- See Also: LRN-20260304-002

---
## [ERR-20260304-002] exact-statement-progress-check-python-missing

**Logged**: 2026-03-04T11:21:30+08:00
**Priority**: low
**Status**: pending
**Area**: workflow

### Summary
在定时进展巡检里尝试用 `python` 做文件存在性统计，当前主机仅有 `python3`，导致命令失败中断该步骤。

### Error
```
/bin/bash: 行 6: python: 未找到命令
```

### Context
- 场景：`/home/gc/Exact-Statement` 的 13 页文件核对脚本。
- 原因：脚本写成 `python - <<'PY'`，但环境中 `python` 别名不存在。

### Suggested Fix
- 统一改用 `python3`，或纯 shell 实现避免解释器别名依赖。

### Metadata
- Reproducible: yes
- Related Files: .learnings/ERRORS.md
- See Also: none

---
## [ERR-20260306-001] bash_printf_double_dash

**Logged**: 2026-03-06T10:28:00+08:00
**Priority**: low
**Status**: pending
**Area**: docs

### Summary
使用 `printf '-- before --\\n'` 在 bash 下报 `invalid option`。

### Error
```
/bin/bash: line 2: printf: --: invalid option
printf: usage: printf [-v var] format [arguments]
```

### Context
- Command/operation attempted: 在 shell 里打印以 `--` 开头的提示文本
- Fix: 改用 `echo`，或写成 `printf '%s\n' '-- before --'`

### Suggested Fix
以后输出以连字符开头的固定字符串时，避免直接把它当作 printf 的格式串。

### Metadata
- Reproducible: yes
- Related Files: none

---
## [ERR-20260306-002] python_tomllib_missing

**Logged**: 2026-03-06T10:31:00+08:00
**Priority**: low
**Status**: pending
**Area**: infra

### Summary
在当前环境调用 `python3` 解析 toml 时，`tomllib` 模块不可用。

### Error
```
ModuleNotFoundError: No module named 'tomllib'
```

### Context
- Command/operation attempted: 用 `python3` + `tomllib` 读取 `~/.codex/config.toml`
- Environment detail: 当前 `python3` 不是自带 `tomllib` 的版本

### Suggested Fix
后续优先用 shell 检查简单配置，或显式使用 `python3.11+` / 安装兼容 toml 解析库。

### Metadata
- Reproducible: yes
- Related Files: /home/gc/.codex/config.toml

---
