# Watchdog Rules (v1)

## Purpose

v1 watchdog does not need to auto-fix everything. Its first job is to **classify task health correctly**.

## Minimum checks

Before reporting that a task is still progressing, check:

1. Has the run file been updated recently?
2. Have recent events been appended?
3. If a lease exists, is it still valid?
4. If executor/session/process signals are available, is the executor still alive?
5. If the task depends on browser/gateway/API/session health, is the dependency still usable?

## Classification hints

- Fresh run updates + fresh events + healthy lease => `RUNNING`
- Explicit timed wait / known external delay => `WAITING_EXTERNAL`
- Stale state + missing executor => `STALLED`
- Stale state + broken dependency => `HALTED_DEPENDENCY`
- Explicit human blocker => `WAITING_HUMAN`

## Critical reporting rule

Do **not** report “still progressing” from a stale business-side status file alone.

A status file that says `111 done` only proves the **last known checkpoint**, not that execution is still alive.

## Suggested v1 heuristic

Treat a task as suspicious if both are true:
- no meaningful state/event refresh within the expected window
- no evidence that the executor is still alive

When suspicious:
- stop optimistic progress reporting
- mark `STALLED` or `HALTED_DEPENDENCY`
- record the reason code
- render a brief with the recommended next action
