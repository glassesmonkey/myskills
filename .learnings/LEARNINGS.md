# Learnings

Corrections, insights, and knowledge gaps captured during development.

**Categories**: correction | insight | knowledge_gap | best_practice
**Areas**: frontend | backend | infra | tests | docs | config
**Statuses**: pending | in_progress | resolved | wont_fix | promoted | promoted_to_skill

## Status Definitions

| Status | Meaning |
|--------|---------|
| `pending` | Not yet addressed |
| `in_progress` | Actively being worked on |
| `resolved` | Issue fixed or knowledge integrated |
| `wont_fix` | Decided not to address (reason in Resolution) |
| `promoted` | Elevated to CLAUDE.md, AGENTS.md, or copilot-instructions.md |
| `promoted_to_skill` | Extracted as a reusable skill |

## Skill Extraction Fields

When a learning is promoted to a skill, add these fields:

```markdown
**Status**: promoted_to_skill
**Skill-Path**: skills/skill-name
```

Example:
```markdown
## [LRN-20250115-001] best_practice

**Logged**: 2025-01-15T10:00:00Z
**Priority**: high
**Status**: promoted_to_skill
**Skill-Path**: skills/docker-m1-fixes
**Area**: infra

### Summary
Docker build fails on Apple Silicon due to platform mismatch
...
```

## [LRN-20260309-005] best_practice

**Logged**: 2026-03-09T23:45:00+08:00
**Priority**: high
**Status**: resolved
**Area**: infra

### Summary
Cron-style quiet tasks must not send acknowledgement text when the command succeeds; return with no visible reply unless an alert is explicitly required.

### Details
A cron-triggered task asked to run `git -C /home/gc/kb/obsidian-vault pull --rebase --autostash` and exit quietly on success, only announcing on error. The command later succeeded (`Already up to date.`), but I still produced a visible acknowledgement instead of staying silent. That violated the requested success behavior and caused the cron task to be treated as incomplete.

### Suggested Action
- For quiet cron jobs, treat successful execution as "no user-facing message" unless the caller explicitly asks for confirmation.
- If I need extra internal verification, do it inside the tool call chain and only surface a message when the failure path triggers.
- When the tool output already proves success, do not add conversational filler.

### Metadata
- Source: user_feedback
- Related Files: .learnings/LEARNINGS.md
- Tags: cron, quiet-success, acknowledgements, correction

---


**Logged**: 2026-03-09T23:13:53+08:00
**Priority**: high
**Status**: resolved
**Area**: config

### Summary
Diagnosing `sessions_spawn` based only on the visible tool list can be misleading because command/runtime paths may still be able to spawn subagents.

### Details
I initially concluded that `sessions_spawn` was unavailable because this chat's explicit tool surface only showed `sessions_list`, `sessions_history`, and `sessions_send`. After restart and a real test, subagent spawning succeeded. This means the missing piece was not necessarily gateway config or runtime capability; it may have been a mismatch between the model-visible tool manifest for this session and the command/runtime dispatch path that can still create subagents.

### Suggested Action
- When checking spawn availability, distinguish between:
  1) model-visible first-class tools in the current session, and
  2) gateway/runtime command paths that can also spawn subagents.
- Do not state "spawn is unavailable" unless both layers are checked or a real spawn attempt fails.
- Prefer a direct live spawn test over inference from tool-list absence.

### Metadata
- Source: user_feedback
- Related Files: .learnings/LEARNINGS.md
- Tags: sessions_spawn, tool-surface, runtime-dispatch, correction

---

## [LRN-20260226-001] correction

**Logged**: 2026-02-26T02:17:29+08:00
**Priority**: high
**Status**: resolved
**Area**: docs

### Summary
在 backlink runbook 测试中把“仅导航验证”误标为 DONE，容易被误解为“留言成功”。

### Details
用户询问“你确定留言成功了没？”指出结果定义不准确。此前执行仅包含访问 URL + 抓取标题，并未完成注册/发帖/评论提交，也未验证公开落地页。将其写为 DONE 会污染状态数据。

### Suggested Action
- 仅导航连通性测试应写 `IN_PROGRESS` 或 `SKIP | reason=connectivity_test_only`，不得写 DONE。
- 只有完成真实提交且可给出落地页 URL，才写 DONE 并填 I 列。
- 如遇风控/验证码，写 NEED_HUMAN。

### Metadata
- Source: user_feedback
- Related Files: backlink-runbook.md
- Tags: state-machine, backlink, validation

---

## [LRN-20260226-001] correction

**Logged**: 2026-02-26T14:43:30+08:00
**Priority**: high
**Status**: pending
**Area**: config

### Summary
Backlink runner must enforce strict serial processing to avoid multiple IN_PROGRESS rows.

### Details
User pointed out rows 2 and 3 were both IN_PROGRESS. This happened because run_one_row.sh was invoked repeatedly and claim_next did not guard against existing IN_PROGRESS rows. Skill text also did not explicitly state mandatory serial guard behavior.

### Suggested Action
1) Add explicit serial-only rule in SKILL.md. 2) Add claim guard in run_one_row.sh to refuse new claims when any IN_PROGRESS exists.

### Metadata
- Source: user_feedback
- Related Files: skills/backlink-excel-runner/SKILL.md, skills/backlink-excel-runner/scripts/run_one_row.sh
- Tags: backlink, state-machine, serial-processing, correction

---

## [LRN-20260226-002] correction

**Logged**: 2026-02-26T23:46:00+08:00
**Priority**: high
**Status**: resolved
**Area**: backend

### Summary
backlink runner 仅实现了“超时回收锁”，未实现“超时重试上限后跳过”，导致单行可长期反复 IN_PROGRESS。

### Details
用户指出“按 skill 应该超过时限就跳过”。实际代码中：
- stale IN_PROGRESS 会被改为 RETRY_PENDING
- 但会再次优先 claim 同一行，且未累计 retry 上限
结果是可在同一行反复循环，pending 长时间不下降。

### Suggested Action
- 在 run_one_row.sh 中加入 `maxRetryPerRow`（默认 3）。
- stale 回收时写入 `retry=<n>`；达到上限后强制 `NEED_HUMAN | reason=retry_exceeded_after_lock_timeout` 并继续下一行。
- 在 SKILL.md/references/recovery.md 同步该规则。

### Metadata
- Source: user_feedback
- Related Files: skills/backlink-excel-runner/scripts/run_one_row.sh, skills/backlink-excel-runner/SKILL.md, skills/backlink-excel-runner/references/recovery.md, memory/backlink-runs/task.json
- Tags: backlink, timeout, retry-budget, state-machine, correction

---
## [LRN-20260303-001] correction

**Logged**: 2026-03-03T23:25:12+08:00
**Priority**: medium
**Status**: pending
**Area**: docs

### Summary
Skill inventory contained an uninstalled skill (image-gen) and was reported as available.

### Details
In group chat, user (Alex) corrected that image-gen skill had been uninstalled. Verification showed path missing: ~/.openclaw/workspace/skills/image-gen. Future capability lists should verify installed/available skills rather than relying on stale injected list assumptions.

### Suggested Action
Before listing optional/custom skills, verify existence of local skill directories when uncertainty exists; explicitly mark unavailable skills as removed.

### Metadata
- Source: user_feedback
- Related Files: .learnings/LEARNINGS.md
- Tags: correction, skills, inventory, image-gen

---
## [LRN-20260303-002] correction

**Logged**: 2026-03-03T23:51:30+08:00
**Priority**: medium
**Status**: pending
**Area**: config

### Summary
When Telegram reaction call fails, do not retry repeatedly; acknowledge once and switch to text fallback.

### Details
User observed runtime warning: message 410, emoji 👀 failed. During testing, repeated `message(action=react)` retries produced the same validation error, creating noisy failures without adding value.

### Suggested Action
- Attempt Telegram reaction once per message.
- If failure repeats with same validation error, stop retries immediately.
- Inform user and use textual fallback (e.g., "👀 处理中") until integration is fixed.

### Metadata
- Source: user_feedback
- Related Files: .learnings/LEARNINGS.md, .learnings/ERRORS.md
- Tags: telegram, reaction, retry-control, correction

---


## [LRN-20260304-001] correction

**Logged**: 2026-03-04T01:19:15+08:00
**Priority**: high
**Status**: pending
**Area**: workflow

### Summary
执行优先级需严格遵守：research-first 重写未全部完成前，禁止推进 Plan-80。

### Details
用户明确纠正："当research全部完成后才做plan80"。此前助理在汇报中仍提到 Plan-80 下一步，和最新指令冲突。后续必须锁定顺序：
1) 完成已提交页面的 research-first 复盘与重写；
2) 仅在全部完成并获用户确认后再启动 Plan-80。

### Suggested Action
- 在进度汇报模板中加入硬校验：若 research 阶段未完成，"下一步"不得出现 Plan-80 执行项。
- 将该优先级写入长期记忆并在每次汇报前自检。

### Metadata
- Source: user_feedback
- Related Files: MEMORY.md, memory/2026-03-03.md, SEO-PLAN-STATUS.md
- Tags: correction, priority, sequencing, plan80, research-first

---

## [LRN-20260304-002] correction

**Logged**: 2026-03-04T09:31:23+08:00
**Priority**: high
**Status**: pending
**Area**: workflow

### Summary
用户要求“改汇报样式后继续执行”，但我未立即转入实作，出现“承诺改进→执行停滞”的断档。

### Details
用户指出“改成这套，然后你为什么停止干活了”。问题根因：
1) 我把“汇报格式优化”当成主要动作，忽略了“持续推进任务本体”；
2) 缺少“每次汇报后必须附带实作增量”的硬约束；
3) 在无新增 commit 周期，没有主动说明正在推进的具体子任务（仅重复状态）。

### Suggested Action
- 立即执行“双轨硬约束”：
  1) 汇报轨：严格使用“与上次相比”增量格式；
  2) 执行轨：每个汇报周期至少完成一个可验证动作（研究文档新增、重写文件修改、QA 校验、或明确阻塞证据）。
- 若确实无提交增量，必须给出“当前具体动作 + 下一个可交付时间点”，禁止空转式复述。
- 将该规则推广到 AGENTS.md 的汇报规范，防止再次发生。

### Metadata
- Source: user_feedback
- Related Files: .learnings/LEARNINGS.md, AGENTS.md, memory/2026-03-04.md
- Tags: correction, execution-gap, reporting, accountability

---

## [LRN-20260304-003] correction

**Logged**: 2026-03-04T11:24:30+08:00
**Priority**: high
**Status**: pending
**Area**: workflow

### Summary
gemini CLI 在本任务里并非“总是卡住”，主要是我频繁 watchdog 重发导致被误判为卡住/停工。

### Details
从 tmux 历史看：
1) 第一轮失败是 prompt 触发了不可用工具 `run_shell_command`（能力约束问题，不是卡死）；
2) 后续在 `Loaded cached credentials.` 后通常是等待完成输出，我多次过早 `Ctrl+C` 并重发，造成“看起来一直停在 shell/反复重启”；
3) 实际已有有效输出文件 `pass-3-gemini-copy-suggestions.md`（11:18）可证明任务完成过。

### Suggested Action
- gemini watchdog 改为“超时阈值 + 文件mtime证据”判定：
  - 若命令启动后 <180s 不重发；
  - 以目标输出文件 mtime 变化作为完成信号；
  - 仅当超过阈值且无新输出时再恢复。
- 在汇报中区分：`失败`（报错退出） vs `等待`（正常运行） vs `完成回到shell`，避免误报“卡住”。

### Metadata
- Source: user_feedback
- Related Files: .learnings/LEARNINGS.md, /home/gc/Exact-Statement/seo-plan/research/rewrite-output/pass-3-gemini-copy-suggestions.md
- Tags: correction, gemini, watchdog, false-positive, process-control

---

## [LRN-20260304-004] correction

**Logged**: 2026-03-04T11:31:10+08:00
**Priority**: high
**Status**: pending
**Area**: config

### Summary
`.bashrc` 存在语法错误（函数定义后缺换行），导致 alias/function 可能失效并引发 shell 行为异常。

### Details
在 `~/.bashrc` 第139行发现 `}alias gemini='gemini --yolo'` 连写，触发解析异常：
`-bash: /home/gc/.bashrc: 行 140: 语法错误：未预期的文件结束符`。
该问题会影响 tmux 会话环境加载，进而干扰对 gemini/codex 启动行为的判断。

### Suggested Action
- 已修复为合法函数定义并补换行：`gemini(){ ... command gemini --yolo ... }`。
- 后续对 shell 配置变更一律执行 `bash -n ~/.bashrc` 校验。

### Metadata
- Source: user_feedback
- Related Files: ~/.bashrc, .learnings/LEARNINGS.md
- Tags: correction, shell, alias, gemini, config

---

## [LRN-20260304-005] correction

**Logged**: 2026-03-04T23:00:00+08:00
**Priority**: high
**Status**: pending
**Area**: workflow

### Summary
当 Codex 任务陷入"无限监控循环"时，我没有及时提醒用户干预，导致用户等待半天。

### Details
- 场景：13页重写完成后，三个 Codex 会话（codex-build/q/frontend）进入"检查变更→没有变更→继续等待"的无限循环
- 问题表现：会话一直输出 NO_CHANGE，但不会自动结束
- 用户的等待时间：约半天（期间我只在定时汇报中反复说"继续等待"，没有主动说"需要干预"）
- 用户反馈："那你当时应该及时提醒我的"、"我等了半天"

### Suggested Action
- 当检测到 Agent 进入"空转循环"（连续多次 NO_CHANGE）时，应立即判断为"需要干预"
- 主动告诉用户："它们在空转，需要手动停掉"
- 不要让用户等一个永远不会结束的结果

### Metadata
- Source: user_feedback
- Related Files: .learnings/LEARNINGS.md, AGENTS.md
- Tags: correction, workflow, agent-monitoring

---

## [LRN-20260305-001] correction

**Logged**: 2026-03-05T00:08:00+08:00
**Priority**: high
**Status**: pending
**Area**: workflow

### Summary
误把"模型响应慢"判断为"卡住"，导致错误反馈给用户。

### Details
- Codex 生成回复需要几分钟，我误以为它卡住了
- 实际上模型只是在处理，需要等待

### Suggested Action
- 以后判断"卡住"用"看输出历史"方法：
  1. 先抓一次 pane 输出并记录
  2. 等几秒/几十秒后再抓一次
  3. 历史没变化 = 真卡了；历史有变化 = 还在处理
- 不要只看 pane_dead 或 process 状态

### Metadata
- Source: user_feedback
- Related Files: .learnings/LEARNINGS.md
- Tags: correction, workflow, agent-monitoring

---

---

## 2026-03-05: Codex + tmux 交互模式 vs exec 模式

### 问题
- 最初用 `exec + pty + background` 模式运行 Codex，执行完任务后自动退出
- 误以为 tmux + Codex 在 OpenClaw 环境不可用

### 根因
- `codex exec` 是一次性调用模式，执行完任务自动退出是预期行为
- 应该用交互式模式：`tmux new-session` + `send-keys 'codex'`

### 解决
正确的工作流：
```bash
# 1. 启动交互式会话
tmux -L cx new -d -s codex-build
tmux -L cx send-keys -t codex-build 'codex' Enter

# 2. 发送任务
tmux -L cx send-keys -t codex-build '任务描述' Enter

# 3. 任务后验收
tmux -L cx display-message -p -t codex-build:0.0 '#{pane_current_command}'
# node = 正常运行，bash = 退出了
```

### 教训
- 不要假设"某种方式不行"，要用实验验证
- Codex exec 模式适合一次性任务，交互模式适合持续对话
- 已将规范写入 AGENTS.md
## [LRN-20260306-001] correction

**Logged**: 2026-03-06T12:49:00+08:00
**Priority**: high
**Status**: pending
**Area**: config

### Summary
验证刚更新的 OpenClaw 环境变量时，不应在当前会话宿主环境直接读取 shell 里的旧值，应优先在 gateway 宿主重新验证。

### Details
用户切换 Notion API key 后，我先在普通 exec 环境中调用 Notion API，看到的是旧 key 可访问的内容，误以为新 key 已生效且权限异常。随后用户指出“那是老 key 可以访问到的内容”，我改用 host=gateway 重新验证，search 结果为 0，说明当前会话默认 shell 环境和 gateway 重启后的真实运行环境可能不一致，至少在重启后验证 secrets 时必须以 gateway 侧结果为准。

### Suggested Action
涉及 gateway config.patch / 重启 / env vars 切换后，所有验证统一走 gateway 宿主（exec host=gateway）或通过网关实际运行面做验证，不要混用本地 shell 环境结论。

### Metadata
- Source: conversation
- Related Files: /home/gc/.openclaw/openclaw.json
- Tags: config, gateway, env, notion, verification

---

## [LRN-20260307-001] correction

**Logged**: 2026-03-07T08:49:42+08:00
**Priority**: medium
**Status**: pending
**Area**: config

### Summary
For read-only knowledge repos that must stay current locally, prefer scheduled pull with push disabled, not fetch-only.

### Details
User clarified their Obsidian vault repo is a knowledge input source and needs local files updated. I initially overemphasized fetch-only safety, which does not update working tree files and therefore may not satisfy the "latest local content" goal.

### Suggested Action
When requirements are "keep local files current" + "never push", set periodic `git pull --rebase --autostash` and hard-disable push URL to prevent accidental push.

### Metadata
- Source: conversation
- Related Files: /home/gc/kb/obsidian-vault/.git/config
- Tags: git, sync, read-only, correction

---
## [LRN-20260308-001] correction

**Logged**: 2026-03-08T18:31:00+08:00
**Priority**: high
**Status**: pending
**Area**: infra

### Summary
有 ProDEX/Codex notify.py 时，不能仅因 agent 长时间扫描仓库、短时无 diff 就判断为空转。

### Details
本次 ballkorokoro.com 保守修复任务中，tmux 多工位 agent 在前期主要进行仓库扫描、定位风险点、读取页面与 locale 内容。我一度把“长时间只读分析、尚未落盘”近似当作“可能空转”，但超哥指出当前环境有 notify.py，理论上不会无意义空转。更准确的判断应基于：pane 输出是否持续推进、是否有 notify、是否有新命令/新阶段，而不是只看有没有立即产出 diff。

### Suggested Action
以后判断 agent 是否空转时，采用更严格标准：
1. 有 notify + pane 输出在推进 + 命令上下文仍变化 → 视为正常工作；
2. 连续多次 capture-pane 输出几乎不变，且没有 notify、没有新命令、没有文件 diff → 才判定为疑似空转；
3. 对大仓库审查类任务，优先发更明确的“直接落盘修改、不要继续只读分析”指令，而不是过早怀疑空转。

### Metadata
- Source: conversation
- Related Files: /home/gc/.openclaw/workspace/TOOLS.md
- Tags: tmux, codex, notify, orchestration, empty-loop

---
## [LRN-20260308-002] correction

**Logged**: 2026-03-08T18:28:00+08:00
**Priority**: high
**Status**: pending
**Area**: infra

### Summary
Codex 的 xhigh 模式做完整任务耗时 10 分钟左右通常是正常现象，不能把“慢”误判为异常。

### Details
超哥明确说明：Codex 的 xhigh 模式干一个活通常都要 10 分钟。这意味着在 tmux 多工位协作时，若模型为 xhigh、任务又涉及仓库扫描/重构/审查，10 分钟级别的无最终产出窗口是正常的，不应仅因耗时长就怀疑 agent 卡死或空转。

### Suggested Action
后续调度 Codex xhigh 时：
1. 默认把 10 分钟级别耗时视为正常工作窗口；
2. 优先看 notify、pane 输出推进、命令阶段变化，而不是只看最终 diff；
3. 只有在长时间无 notify、无输出变化、无新命令、无 diff 时，才判定疑似卡住/空转。

### Metadata
- Source: conversation
- Related Files: /home/gc/.openclaw/workspace/.learnings/LEARNINGS.md
- Tags: codex, xhigh, notify, tmux, orchestration, latency

---
## [LRN-20260308-003] correction

**Logged**: 2026-03-08T18:37:00+08:00
**Priority**: high
**Status**: pending
**Area**: infra

### Summary
超哥要求未来涉及 Codex 协作的改动任务默认走“纯 Codex 模式”，不要再混合成我亲自下刀收尾。

### Details
在 ballkorokoro.com 保守修复任务中，我采用了“Codex 审查 + 我接手关键修复/收尾”的混合模式。超哥随后明确要求：以后走纯 Codex 模式。这意味着对于用户指定 Codex 的任务，我应主要做编排、监控、验收、提交和汇报；除非用户临时授权切回混合模式，否则不应自己直接改代码文件。

### Suggested Action
后续若用户要求 Codex：
1. 默认使用 tmux + Codex 纯代理执行；
2. 我负责拆任务、下指令、监控、处理阻塞、验收、提交和推送；
3. 不亲自修改代码，除非用户明确说可以切换为混合模式或手动接管；
4. 若 Codex 长时间只分析不落盘，应继续通过更硬指令驱动其改文件，而不是自己直接接管。

### Metadata
- Source: conversation
- Related Files: /home/gc/.openclaw/workspace/AGENTS.md
- Tags: codex, orchestration, pure-codex-mode, tmux

---
## [LRN-20260309-004] correction

**Logged**: 2026-03-09T06:55:00+08:00
**Priority**: high
**Status**: pending
**Area**: docs

### Summary
涉及网站文案/SEO 优化时，不能只做保守清理；如果用户之前已经要求按关键词/搜索意图去优化文案，就必须先做真实外部搜索调研并据此改文案。

### Details
在 ballkorokoro.com 的日语任务里，我主要推动了“删除假评分、清模板残留、保守修文案”的清理流，但没有先去网上搜索目标关键词、竞品页、搜索意图、PAA，再据此优化日语文案。这违反了超哥明确强调过的 research-first 规则，也偏离了“你之前安排过”的要求。

### Suggested Action
后续凡是文案/SEO/落地页任务：
1. 先明确关键词与语言范围；
2. 先做外部搜索调研（SERP、竞品、PAA、搜索意图）；
3. 把调研结果写入 research/<topic>.md；
4. 再让 Codex 按调研结论改文案；
5. 若这一步未完成，不能把任务汇报成“文案优化已完成”。

### Metadata
- Source: conversation
- Related Files: /home/gc/.openclaw/workspace/AGENTS.md, /home/gc/.openclaw/workspace/MEMORY.md
- Tags: seo, copywriting, research-first, correction, ballkorokoro

---

## [LRN-20260309-001] best_practice

**Logged**: 2026-03-09T16:48:00+08:00
**Priority**: high
**Status**: pending
**Area**: infra

### Summary
多 tmux/Codex 持续任务在“上一轮已答完但未收到下一轮明确指令”时，会表现为会话存活但空转；必须使用显式 handoff/state 机制避免任务推进断裂。

### Details
本次 ballkorokoro 任务中，多个 Codex tmux session 的 node 进程仍在，但输出已经停在总结/待命提示符。根因不是进程挂死，而是：上一轮任务结束后没有把新的执行目标（research-first 的日语改稿）重新明确下发到对应 session，导致系统表面上“还活着”，实际上没有继续产出。

### Suggested Action
- 持续任务必须有单独状态文件（当前阶段、owner、下一步、阻塞、验收标准）。
- 每个 tmux session 只负责单一角色，且每轮任务结束必须写一段明确 handoff。 
- 连续两次检查无文件变更即判定停滞，不允许重复汇报“阻塞中”；必须执行 steer / 重新派单 / 关停回收中的一个动作。
- 汇报前必须核对 git diff、目标文件 mtime、pane 输出，而不是凭记忆。

### Metadata
- Source: simplify-and-harden
- Related Files: AGENTS.md, .learnings/LEARNINGS.md
- Tags: tmux, codex, task-orchestration, handoff, idle-session, best-practice
- Pattern-Key: task.handoff-prevents-idle-sessions
- Recurrence-Count: 1
- First-Seen: 2026-03-09
- Last-Seen: 2026-03-09

---

## [LRN-20260309-002] correction

**Logged**: 2026-03-09T22:21:00+08:00
**Priority**: high
**Status**: pending
**Area**: infra

### Summary
涉及编程的任务必须交给 Codex 执行；主 session 负责任务编排、状态管理、验收和汇报，不应越界直接承担编码实现。

### Details
用户明确要求“涉及编程的任务必须用 codex, 术业有专攻, 别越界, 你就负责任务编排”。此前在 ballkorokoro JP rewrite 中，虽然使用了新的 task-governance skill，但实际代码和文案修改由主 session 直接完成，没有把实现层交给 Codex/ACP。这违背了用户对职责分工的明确要求。

### Suggested Action
- 后续凡属编程/改代码/改页面实现类任务，默认由 Codex 执行（优先 ACP 方案，其次按用户要求的 Codex 通道）。
- 主 session 仅负责：任务 intake、拆分、派单、状态文件、进度跟踪、QA 验收、结果汇总。
- 若想亲自改一处一行级小修，也应先确认是否属于“无需 Codex 的简单修改”；否则默认不要直接下手。

### Metadata
- Source: user_feedback
- Related Files: skills/task-execution-tracker/SKILL.md, skills/multi-acp-collaboration/SKILL.md
- Tags: codex, orchestration, role-boundary, correction

---
