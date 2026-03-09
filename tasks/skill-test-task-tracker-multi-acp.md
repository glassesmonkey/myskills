# Task: skill-test-task-tracker-multi-acp

## Goal
- Verify the minimum working path required by `task-execution-tracker` and `multi-acp-collaboration` in the current Telegram group control-chat context.

## Deliverables
- A task state file exists and is updated before reporting.
- Role split / labels / done definition are explicit.
- Real capability checks are recorded with evidence.
- A final pass/block report is produced.

## Current Phase
- blocked

## Owner
- main-controller

## Done Definition
- [x] Task state file created.
- [x] Goal / done definition / non-goals / worker map written down.
- [x] Capability checks run for subagent / ACP execution path.
- [x] Evidence gathered from docs + runtime tool visibility.
- [ ] Spawn at least one ACP worker session successfully.
- [ ] Receive at least one worker handoff through the control-chat flow.

## Non-goals
- Do not change gateway config.
- Do not send slash commands into the user chat just to force a spawn.
- Do not pretend a docs-only result equals a real ACP execution result.

## Current Status
- Last real change: 2026-03-10 06:51 Asia/Shanghai — created task file, inspected skills/docs, checked runtime session/agent visibility.
- Current blocker: current tool surface in this chat exposes `agents_list`, `sessions_list`, `sessions_history`, `sessions_send`, but no callable `sessions_spawn` / `subagents` tool from the assistant runtime, so true ACP worker spawning cannot be executed from this turn.
- Next action: report pass/block split clearly; if needed, perform operator-triggered `/acp spawn ...` validation in chat or enable the missing spawn capability for this runtime.
- Next check trigger: user asks to continue ACP path verification.

## TODO
- [x] Read the two skill files and extract required checks.
- [x] Create a task state file before reporting.
- [x] Verify allowed agent ids.
- [x] Verify visible sessions.
- [x] Verify OpenClaw docs for ACP/subagent spawn behavior.
- [ ] Spawn ACP research worker.
- [ ] Spawn ACP implement worker.
- [ ] Verify handoff summaries routed back to control chat.

## Worker Map
- skill-test-control: controller / aggregation
- skill-test-research: capability + docs inspection
- skill-test-implement: ACP spawn execution check (blocked)
- skill-test-qa: validate handoff / summary format (pending)

## Latest Handoff
### 2026-03-10 06:51
Done:
- Read `multi-acp-collaboration` and `task-execution-tracker` skill requirements.
- Verified the state-file template and created this task file.
- Checked official OpenClaw docs: ACP sessions require `sessions_spawn` with `runtime: "acp"` or `/acp spawn`.
- Checked runtime visibility: `agents_list` returns only `main`; `sessions_list` returns no active ACP/subagent sessions.
- Confirmed current assistant tool surface does not expose a callable `sessions_spawn` / `subagents` function in this runtime.

Not done:
- Real ACP worker creation.
- Multi-worker control-chat summary loop.

Blocker:
- Missing spawn capability in the assistant runtime for this chat/session.

Next recommended action:
- If you want a full end-to-end ACP validation, we need either:
  1. assistant-side `sessions_spawn` / `subagents` capability exposed in this runtime, or
  2. an operator-triggered `/acp spawn ...` test from chat, after which I can continue with status / steer / verification.
