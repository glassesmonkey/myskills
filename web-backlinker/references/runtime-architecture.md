# Runtime Architecture

## Why this exists

Web Backlinker should not rely on one giant uninterrupted chat turn to process a whole target list. Browser work, signup flows, and email verification are too fragile for that model.

It also should not pay the full context cost for every single row. Use a recoverable runtime architecture that keeps durable local state, a compact handoff brief, and a small-batch worker loop instead.

## Core design

### 1. Small-batch drain worker
A worker should process a **small batch** of target URLs per run, not the whole sheet and not exactly one row forever.

Recommended v1 limits:
- up to **3 rows** per worker run
- at most **1 deep submit** path in that run
- the other slots should stay lightweight scout / classify / quick-park work

The worker may:
- scout a site
- continue an existing signup flow
- continue email verification
- continue a submission flow
- finish one or more rows in terminal or holding states

The worker should not try to finish the whole batch.

### 2. Local task store
Persist task state outside chat history and outside in-memory `exec/process` sessions.

Recommended location:

```text
data/web-backlinker/tasks/
  <run-id>-current-run.json
  <run-id>-events.jsonl
  <run-id>-current-run-lease.json
  <run-id>-worker-brief.json
```

A task entry should include at least:
- `task_id`
- `row_id`
- `domain`
- `normalized_url`
- `status`
- `phase`
- `strategy`
- `attempts`
- `last_error`
- `reason_code`
- `route`
- `artifact_ref`
- `sheet_status`
- `last_progress_at`
- `updated_at`
- `locked_by`
- `lock_expires_at`
- `playbook_id`
- `notes` (trimmed recent notes only)

### 3. Batch lease
Do not rely on row locks alone when the batch can be triggered repeatedly.

Use a **batch lease** to ensure only one worker is draining the batch at a time.

Recommended lease fields:
- `run_id`
- `owner_worker`
- `started_at`
- `heartbeat_at`
- `expires_at`
- `processed_count`
- `last_task_id`
- `state`

Rules:
- worker acquires the lease before claiming rows
- worker heartbeats the lease after each completed row or major checkpoint
- worker releases the lease on normal exit
- watchdog reclaims expired leases when the owner is gone

### 4. Compact worker brief
Do not make every worker reread the full manifest, full product profile, and long event history.

Generate a compact `worker-brief.json` before execution. It should contain only:
- run summary and current counts
- top candidate rows for this worker run
- compact product profile fields needed for truthful submission
- a few recent events
- hard rules

This brief is the default entry point for the worker.

### 5. Watchdog / summary separation
Do not make the periodic monitor perform the entire browser workflow.

Instead:
- watchdog checks whether work is progressing
- watchdog reclaims stale leases/tasks when needed
- watchdog posts or stores summary updates
- worker does the actual target-specific work

### 6. Heartbeat role
Heartbeat is for checking whether the system is alive or whether a reminder should be sent. It is not the primary execution engine.

Use heartbeat for:
- “is anything stuck?”
- “has there been progress recently?”
- “send a reminder if idle too long”

Do not use heartbeat as the only place where submissions actually happen.

### 7. Model tiering
Use different model tiers for different kinds of work.

Recommended split:
- **Cheap model**: watchdog, manifest/summary note compression, first-layer triage of obvious blockers, scope mismatches, and known playbook-backed failures.
- **Strong model**: deep submit flows, duplicate-sensitive decisions, nuanced route selection, and any step where incorrect product claims or unsafe external writes would be costly.

The cheap model should only classify, compress, or park work. It should not perform authenticated submissions or improvise product facts.

## Time budget model

Use two clocks:

### Total worker timeout
Recommended:
- `900-1200s`

Purpose:
- upper bound for one small-batch worker run

### Per-row budget
Recommended:
- fast scout / quick-park row: `120-180s`
- deep submit row: `300-420s`

Purpose:
- stop one difficult row from eating the whole worker budget

### Progress checkpoint expectation
Recommended:
- every `60-120s`

Purpose:
- worker should write meaningful progress regularly

### Stalled threshold
Recommended:
- `300s` without progress means “likely stalled”

Purpose:
- watchdog decides whether to recover or retry

## Recovery logic

If a task is `RUNNING` or `SCOUTING` but has no progress beyond the stalled threshold:
1. mark it as stalled/recoverable
2. record the last known phase and reason code
3. requeue or retry it with attempt count incremented
4. continue with another executable task if appropriate

If a lease is still active and healthy:
- do not start another draining worker for the same run

If the lease is expired and backlog remains:
- reclaim the lease
- start one new worker

If a task failed because of site-side error:
- keep artifact evidence
- preserve the partially learned playbook
- mark for retry later instead of pretending nothing was learned

## Recommended worker loop

1. acquire batch lease
2. read `worker-brief.json`
3. claim next executable row
4. checkpoint phase start
5. do one row’s scouting/execution work
6. write terminal or holding state
7. heartbeat lease
8. repeat until one of these is true:
   - 3 rows processed
   - 1 deep submit already consumed and budget is nearly spent
   - total worker budget reached
   - no executable rows remain
9. batch-sync external surfaces (for example Sheet) once near the end of the run
10. refresh compact manifest summary
11. release lease
12. exit

## Recommended watchdog loop

1. read task store + lease + compact manifest
2. count done/failed/pending/running/stalled
3. if lease is expired and backlog remains, trigger one worker
4. if a row is stale beyond the threshold, mark it `STALLED` / `RETRYABLE`
5. write a concise summary
6. exit

## Anti-patterns to avoid

- one cron job doing full-batch execution + monitoring + reporting
- forcing each worker to reread the full manifest note history
- relying on chat memory as the queue
- treating `exec/process` memory as durable state
- assuming “no error message” means the task is still progressing
- letting a failed target pause the whole batch
- launching concurrent workers for the same run without a lease
- spending the whole worker budget on a CAPTCHA or Cloudflare row
no error message” means the task is still progressing
- letting a failed target pause the whole batch
- launching concurrent workers for the same run without a lease
- spending the whole worker budget on a CAPTCHA or Cloudflare row
