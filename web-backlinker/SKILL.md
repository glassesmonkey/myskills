---
name: web-backlinker
description: Standardize semi-automated backlink operations for a txt list of target URLs. Use when OpenClaw needs to (1) create a Google Sheet control panel for backlink runs, (2) scout and classify directory/community/article-platform targets, (3) execute backlink work as resumable single-URL tasks instead of one giant batch run, (4) persist local task state, playbooks, and artifacts for recovery, or (5) generate a promoted-site profile so submissions and article angles are factual and reusable.
---

# Web Backlinker

Use this skill to turn a backlink target list into a non-blocking, sheet-driven workflow with local memory. Optimize for repeatability, auditable state, crash recovery, and gradual reuse rather than one-off heroic browser sessions.

## Core operating model

- Treat a user-provided txt file as the import format only.
- Treat Google Sheet as the operational control panel and review surface.
- Treat local workspace files as the canonical store for task state, playbooks, product profiles, run manifests, and artifacts.
- Treat secrets/keyring as the only allowed store for passwords or app passwords.
- Treat human-required nodes as row-level detours: mark, report, continue.
- Treat one URL as one recoverable task unit.
- Treat long tasks as checkpointed flows, not as one uninterrupted monolithic run.

## Read these references when needed

- `references/design.md` — overall architecture, object model, workflow, v1/v2 scope
- `references/runtime-architecture.md` — single-URL worker model, watchdog design, time budgets, recovery rules
- `references/sheet-schema.md` — required tabs, columns, and write policy
- `references/state-machine.md` — row, task, and run states plus transition rules
- `references/strategy-rules.md` — site classification, route selection, and browser choice
- `references/product-profiler.md` — how to build the promoted-site profile and keep claims safe
- `references/playbook-memory.md` — local storage layout, playbook schema, learning rules
- `references/status-format.md` — fixed user-visible run/status line formats
- `references/safety-rules.md` — external-write guardrails; read before any signup, submission, or credential handling

## Default workflow

1. Freeze scope.
   - Require the target txt path.
   - Prefer promoted site URL, product name, and contact email.
   - If promoted-site config is incomplete, still create the Sheet and mark the run as waiting for config instead of improvising.

2. Bootstrap local runtime.
   - Run `scripts/bootstrap_run.py` to create `data/web-backlinker/{runs,artifacts,playbooks,product-profiles,tasks}` and emit a run manifest.

3. Create the Google Sheet first.
   - Create the Sheet before long-running work so the user gets an immediate control surface.
   - Return the sheet link immediately using the exact `[WB-INIT]` line from `references/status-format.md`.
   - For Google Sheets / Gmail / Drive operations, read the `gog` skill.

4. Import targets and persist task state.
   - Run `scripts/normalize_targets.py` on the txt input.
   - Write normalized rows into the `Targets` tab.
   - Create/update a local task store with `scripts/task_store.py init ...`.
   - Deduplicate by normalized URL, not just by domain.

5. Build or refresh the promoted-site profile.
   - Read `references/product-profiler.md`.
   - Persist the full profile locally.
   - Mirror review-friendly summary fields into the `ProductProfile` tab.

6. Scout before submitting.
   - Read `references/strategy-rules.md`.
   - Prefer built-in browser control for public reconnaissance.
   - Escalate to Browser Relay for Google OAuth, authenticated flows, and pages that depend on a real session.
   - Persist scouting results into both Sheet and local task state.

7. Execute as single-URL workers.
   - Do not ask one worker to process the whole batch.
   - Claim one executable task from the local task store.
   - Run only that task until it reaches a checkpointed terminal/holding state.
   - Persist progress after each meaningful phase change.

8. Keep the batch non-blocking.
   - On CAPTCHA, Cloudflare challenge, payment walls, reciprocal backlink requirements, phone verification, suspicious flows, or manual-content requirements:
     - update the current row and local task state
     - emit the fixed `[WB-ROW]` line
     - continue with another task in a later worker run

9. Separate worker execution from summary/watchdog reporting.
   - Worker runs should focus on one target URL and local/sheet state updates.
   - Summary/watchdog runs should inspect progress, report status, and only trigger recovery when tasks are stalled.
   - Heartbeat is only for watch-dogging or reminders; do not use heartbeat as the primary execution engine.

10. Learn after every meaningful result.
    - On success, create or update a site playbook locally.
    - When multiple similar sites succeed, promote them into a pattern playbook.
    - Do not let the skill rewrite its own core rules; learn as data, not as autonomous policy changes.

11. Finish cleanly.
    - Emit `[WB-SUMMARY]` at the end of a summary/watchdog cycle.
    - Emit `[WB-HALT]` only for infrastructure-wide failures that make continuing unsafe or impossible.

## Tool selection

- Built-in browser control: lightweight scouting, public page reading, non-auth discovery
- Browser Relay: Google OAuth, authenticated sessions, complex JS flows, shared human browser state
- Gog / Gmail: constrained verification-email lookups only; never roam the whole inbox without need
- Exec + bundled scripts: normalization, run bootstrapping, task state persistence, status formatting, playbook scaffolding

## Browser strategy

- Short term: use Relay selectively for hard auth/session flows.
- Medium term: prefer a managed browser profile for unattended execution.
- Long term: avoid making the extension relay the only recovery path for batch execution.

## Non-negotiable rules

- Never block the whole batch on one row unless the infrastructure is broken.
- Never store passwords in Google Sheet or plaintext playbooks.
- Never auto-pay, auto-accept reciprocal backlink requirements, or attempt CAPTCHA bypasses.
- Never invent product claims; use the promoted-site profile as the source of truth.
- Never treat sheet state as the canonical playbook body; playbook bodies live locally.
- Never treat chat context as the only queue; always persist task state locally.
- Never rely on one giant uninterrupted batch run when single-URL task recovery is possible.

## Bundled scripts

- `scripts/bootstrap_run.py` — create runtime directories and a run manifest
- `scripts/normalize_targets.py` — normalize/dedupe txt inputs into structured rows
- `scripts/render_status.py` — render fixed `[WB-*]` status lines
- `scripts/scaffold_playbook.py` — create a site/pattern playbook stub in local storage
- `scripts/task_store.py` — initialize, claim, checkpoint, finish, and summarize single-URL tasks in local state
