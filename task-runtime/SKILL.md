---
name: task-runtime
description: Create, structure, run, monitor, and recover complex long-running tasks with durable local state. Use when a task is multi-step, likely to stall, depends on external systems or browser/session health, needs resumable execution, or requires explicit health checks / recovery instead of one-shot prompting. Especially useful for: (1) long scraping/rebuild jobs, (2) batch workflows with many items, (3) multi-phase submission/publishing flows, (4) tasks that need progress reporting without stale-status hallucination, and (5) any request to “split this task”, “keep it running”, “resume from where it stopped”, or “find why it stalled”.
---

# Task Runtime

Use this skill as a **minimal execution framework** for complex tasks that should not rely on a single uninterrupted chat turn.

## Core idea

Treat a long task as a durable run with:
- a `run.json` state file
- an `events.jsonl` append-only log
- a compact `brief.json` handoff summary
- an optional `lease.json` for health / ownership

Do **not** treat chat history as the only source of truth.

## Read these references when needed

- `references/run-schema.md` — canonical run / event / brief / lease fields
- `references/state-machine.md` — minimal v1 states and transitions
- `references/watchdog-rules.md` — how to detect stale progress vs healthy waiting
- `references/resume-protocol.md` — how to resume from checkpoints safely

## Default workflow

1. **Intake the task**
   - Clarify goal, scope, success condition, and major dependencies.
   - If the task is not long-running / multi-step / failure-prone, do not force this skill.

2. **Initialize a run**
   - Use `scripts/init_run.py` to create a run directory entry under `data/task-runtime/`.
   - Fill title, goal, task type, initial phase, and any known checkpoint / dependency info.

3. **Set the first executable phase**
   - Do not over-decompose.
   - v1 only needs enough structure to know: current phase, current item (if any), next action, and resume point.

4. **Append events as the task progresses**
   - Use `scripts/append_event.py` for meaningful transitions only.
   - Prefer short, code-first notes over long prose.

5. **Update run state after each real checkpoint**
   - Use `scripts/update_run.py` whenever status, phase, item index, blocker, or recovery point changes.
   - Do not leave waits as raw shell sleeps without also updating state.

6. **Render a compact brief before handoff or recovery**
   - Use `scripts/render_brief.py` to summarize current status, last good checkpoint, blocker, and next action.
   - New workers should read the brief, not the whole history, by default.

7. **Health-check before reporting progress**
   - Use `scripts/check_health.py` and `references/watchdog-rules.md`.
   - Never report “still progressing” from a stale business status file alone.
   - Verify at least: recent state freshness, recent events, and whether the executor/session/process is still alive when that signal is available.

8. **Resume from explicit checkpoints**
   - Use `references/resume-protocol.md`.
   - Recovery must state: last good checkpoint, current blocker, dependency health, and resume point.

## v1 state philosophy

Keep the state machine small. Use these run states unless a task truly needs more:
- `CREATED`
- `READY`
- `RUNNING`
- `WAITING_EXTERNAL`
- `WAITING_HUMAN`
- `STALLED`
- `HALTED_DEPENDENCY`
- `COMPLETED`
- `FAILED`

## Non-negotiable rules

- Never let a long task exist only in chat context.
- Never treat `sleep N` as a complete waiting model; waiting must be reflected in run state.
- Never base progress reporting only on a stale `status.json` from the business workflow.
- Never claim a task is still running if state is stale and the executor is gone.
- Never resume “from memory”; resume from explicit checkpoints and recent events.
- Never overbuild v1. Prefer a minimal, inspectable runtime over a smart but fragile system.

## Good fit examples

- WeChat / browser-driven rebuild jobs that may stall on browser or gateway dependencies
- Batch submission or scraping tasks with item-by-item checkpoints
- Long research → extract → transform → publish workflows
- Any task where the user asks to keep execution going over time and recover from stalls

## Poor fit examples

- Single-turn one-off tasks
- Tiny edits that do not need health checks or resumability
- Pure reminders with no execution body
