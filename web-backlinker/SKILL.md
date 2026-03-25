---
name: web-backlinker
description: Standardize semi-automated backlink operations for a txt list of target URLs. Use when OpenClaw needs to (1) create a Google Sheet control panel for backlink runs, (2) scout and classify directory/community/article-platform targets, (3) execute backlink work as resumable small-batch drain workers (up to 3 URLs per run) instead of one giant batch run, (4) persist local task state, playbooks, leases, manifests, and artifacts for recovery, or (5) collect/init a reusable promoted-site submission profile before backlink execution so later rows do not stall on missing company facts, emails, or policy choices.
---

# Web Backlinker

Use this skill to turn a backlink target list into a non-blocking, sheet-driven workflow with local memory. Optimize for repeatability, auditable state, crash recovery, and gradual reuse rather than one-off heroic browser sessions.

## Core operating model

- Treat a user-provided txt file as the import format only.
- Treat Google Sheet as the operational control panel and review surface.
- Treat local workspace files as the canonical store for task state, playbooks, product profiles, run manifests, artifacts, account registry metadata, and the cross-run submission ledger.
- Treat secrets/keyring as the only allowed store for passwords or app passwords.
- Treat `browser-use` direct CLI as an optional fast path for stable, replayable directory flows — never as the only browser path.
- Treat human-required nodes as row-level detours: mark, report, continue.
- Treat one URL as one recoverable task unit.
- Treat long tasks as checkpointed flows, not as one uninterrupted monolithic run.
- Treat promoted-site initialization as a first-class phase, not as ad-hoc Q&A in the middle of worker execution.

## Read these references when needed

- `references/init-intake.md` — required initialization fields, policy boundaries, normalization rules, and `WAITING_CONFIG` gating
- `references/design.md` — overall architecture, object model, workflow, v1/v2 scope
- `references/runtime-architecture.md` — small-batch drain worker model, batch lease, worker brief, watchdog design, time budgets, and recovery rules
- `references/sheet-schema.md` — required tabs, columns, and write policy
- `references/state-machine.md` — row, task, and run states plus transition rules
- `references/strategy-rules.md` — site classification, route selection, and browser choice
- `references/product-profiler.md` — how to build the promoted-site profile and keep claims safe
- `references/playbook-memory.md` — local storage layout, playbook schema, learning rules
- `references/browser-use-fast-path.md` — when to compile stable directory flows into a low-token `browser-use` direct-execution lane
- `references/account-registry.md` — how to reuse site accounts without storing raw passwords in playbooks or sheets
- `references/status-format.md` — fixed user-visible run/status line formats
- `references/safety-rules.md` — external-write guardrails; read before any signup, submission, or credential handling

## Default workflow

1. Freeze scope.
   - Require the target txt path.
   - Prefer promoted site URL, product name, and contact email.
   - Read `references/init-intake.md` before starting the real run.
   - Collect the required intake fields first instead of waiting for later blockers to expose them.
   - If intake is incomplete, still create the Sheet and import targets, but mark the run `WAITING_CONFIG` instead of improvising.

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
   - Deduplicate by normalized URL inside the imported txt, not just by domain.
   - Pass `--submission-ledger <manifest.submission_ledger_path> --promoted-url <canonical promoted url>` during init so previously submitted targets for the same promoted site are parked before execution.

5. Build or refresh the promoted-site profile.
   - Read `references/product-profiler.md`.
   - Persist the full profile locally.
   - Include not only marketing copy, but also submission identity, disclosure preferences, and company-email rules from the intake step.
   - Mirror review-friendly summary fields into the `ProductProfile` tab.

6. Respect `WAITING_CONFIG` gating.
   - While the run is `WAITING_CONFIG`, allow only non-writing setup work: sheet creation, target import, partial profile building, and light scouting.
   - Do not start signup, submission, claim, or verification steps that would force guessing company facts, contact identity, or disclosure policy.
   - When the missing intake arrives, update the profile first, then resume execution.

7. Scout before submitting.
   - Read `references/strategy-rules.md`.
   - Prefer built-in browser control for public reconnaissance.
   - Escalate to Browser Relay for Google OAuth, authenticated flows, and pages that depend on a real session.
   - Persist scouting results into both Sheet and local task state.

8. Compile replayable site memory when a path looks reusable.
   - Read `references/browser-use-fast-path.md` and `references/account-registry.md` when a site appears stable enough for reuse.
   - Reuse existing per-domain accounts before opening a new signup path.
   - Compile the discovered path into a site playbook with field mappings, direct steps, result checks, and fallback route.
   - Validate the playbook before promoting it into a fast path.

9. Prepare a compact worker brief before execution.
   - Generate a `worker-brief.json` with `scripts/prepare_worker_brief.py`.
   - Put only the current counts, top candidate rows, compact product profile, and a few recent events into the brief.
   - Do not make each worker reread the whole manifest, event log, and profile history.

9. Execute as small-batch drain workers.
   - Do not ask one worker to process the whole batch.
   - Acquire the batch lease before claiming rows.
   - Process up to 3 executable tasks in one run, but allow at most 1 deep submit path.
   - Treat the other slots as fast scout / fast park work.
   - Keep a total worker budget of roughly 15 minutes and checkpoint after each meaningful phase change.

10. Keep the batch non-blocking.
   - On CAPTCHA, Cloudflare challenge, payment walls, reciprocal backlink requirements, phone verification, suspicious flows, or manual-content requirements:
     - update the current row and local task state
     - emit the fixed `[WB-ROW]` line
     - park the row quickly instead of burning the whole worker budget
     - continue with another task in the same worker run when safe
   - For reciprocal backlink / link-exchange requirements specifically:
     - record the site as a later-review candidate
     - do not proactively submit or auto-accept the exchange
     - leave enough evidence for later manual selection

11. Separate worker execution from summary/watchdog reporting.
   - Worker runs should focus on the selected small batch plus local state updates.
   - Summary/watchdog runs should inspect progress, report status, reclaim stale leases/tasks, and only trigger recovery when work is actually stuck.
   - Heartbeat is only for watch-dogging or reminders; do not use heartbeat as the primary execution engine.

12. Learn after every meaningful result.
   - On success, create or update a site playbook locally.
   - When a row reaches `SUBMITTED`, `PENDING_EMAIL`, `VERIFIED`, or an already-listed outcome, call `scripts/task_store.py finish ... --submission-ledger <manifest.submission_ledger_path> --promoted-url <canonical promoted url>` so later runs do not resubmit the same promoted site to the same target.
   - When multiple similar sites succeed, promote them into a pattern playbook.
   - When a run stalls because setup info was missing, improve the intake checklist instead of relying on repeated ad-hoc questioning.
   - Do not let the skill rewrite its own core rules; learn as data, not as autonomous policy changes.

13. Finish cleanly.
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
- Never start external-write steps when the run is still `WAITING_CONFIG`.

## Bundled scripts

- `scripts/bootstrap_run.py` — create runtime directories, a run manifest, and expose the shared submission-ledger path
- `scripts/normalize_targets.py` — normalize/dedupe txt inputs into structured rows
- `scripts/render_status.py` — render fixed `[WB-*]` status lines
- `scripts/scaffold_playbook.py` — create a site/pattern playbook stub in local storage
- `scripts/compile_site_playbook.py` — create/update a site playbook with execution-mode, field-map, direct-step, and fallback metadata
- `scripts/validate_site_playbook.py` — validate a site playbook before trusting it as a fast path
- `scripts/run_site_playbook.py` — replay a `browser_use_direct` playbook against a product profile
- `scripts/select_execution_plan.py` — choose route / execution_mode / automation_disposition from task + playbook + account-registry state
- `scripts/browser_use_safe.sh` — hardened `browser-use` CLI wrapper with env loading, reset, retry, and log capture
- `scripts/browser_use_smoke.sh` — smoke-test the direct CLI lane before rollout or after environment changes
- `scripts/account_registry.py` — persist reusable per-domain account metadata without storing raw passwords in playbooks
- `scripts/task_store.py` — initialize, claim, checkpoint, finish, summarize tasks, select next candidates, manage the batch lease, and maintain the cross-run submission ledger
- `scripts/prepare_worker_brief.py` — generate a compact `worker-brief.json` so each worker reads only the top candidates and minimal profile context
- `scripts/update_run_manifest.py` — refresh the compact run manifest summary, counts, and recent notes without keeping an ever-growing note history
