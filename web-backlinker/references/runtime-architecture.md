# Runtime Architecture

## Why this exists

Web Backlinker should not rely on one giant uninterrupted chat turn to process a whole target list. Browser work, signup flows, and email verification are too fragile for that model.

Use a recoverable runtime architecture instead.

## Core design

### 1. Single-URL worker
A worker should process exactly one target URL per run.

The worker may:
- scout the site
- continue an existing signup flow
- continue email verification
- continue a submission flow
- finish the task in a terminal state

The worker should not try to finish the whole batch.

### 2. Local task store
Persist task state outside chat history and outside in-memory `exec/process` sessions.

Recommended location:

```text
data/web-backlinker/tasks/
  current-run.json
  events.jsonl
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
- `last_progress_at`
- `updated_at`
- `locked_by`
- `lock_expires_at`
- `playbook_id`
- `notes`

### 3. Watchdog / summary separation
Do not make the periodic monitor perform the entire browser workflow.

Instead:
- watchdog checks if work is progressing
- watchdog triggers or resumes a worker if needed
- watchdog posts summary updates
- worker does the actual target-specific work

### 4. Heartbeat role
Heartbeat is for checking whether the system is alive or whether a reminder should be sent. It is not the primary execution engine.

Use heartbeat for:
- “is anything stuck?”
- “has there been progress recently?”
- “send a reminder if idle too long”

Do not use heartbeat as the only place where submissions actually happen.

### 5. Browser evolution path

Short term:
- use Browser Relay for Google OAuth and rescue flows
- use built-in browser control for public scouting

Medium term:
- prefer a managed OpenClaw browser profile for unattended execution

Long term:
- avoid making an extension-attached tab the only way a batch can continue

## Time budget model

Do not use a tiny hard timeout for the total task. A single URL can legitimately take 10-20 minutes.

Use two clocks:

### Total task timeout
Recommended:
- `900-1200s`

Purpose:
- upper bound for one URL worker run

### Progress checkpoint expectation
Recommended:
- every `60-120s`

Purpose:
- worker should write a meaningful checkpoint regularly

### Stalled threshold
Recommended:
- `300s` without progress means “likely stalled”

Purpose:
- watchdog decides whether to recover/retry

## Recovery logic

If a task is `RUNNING` but has no progress beyond the stalled threshold:
1. mark it as stalled/recoverable
2. record the last known phase
3. requeue or retry it with attempt count incremented
4. continue with another executable task if appropriate

If a task failed because of site-side error:
- keep artifact evidence
- preserve the partially learned playbook
- mark for retry later instead of pretending nothing was learned

## Recommended worker loop

1. claim next executable task
2. write `RUNNING` + lock info
3. checkpoint phase start
4. do one target’s scouting/execution work
5. checkpoint meaningful progress after each phase
6. write terminal state or holding state
7. release lock
8. exit

## Recommended watchdog loop

1. read task store + latest summary artifacts
2. count done/failed/pending/running/stalled
3. if no progress within threshold, trigger or resume one worker
4. write a concise summary
5. exit

## Anti-patterns to avoid

- one cron job doing full-batch execution + monitoring + reporting
- relying on chat memory as the queue
- treating `exec/process` memory as durable state
- assuming “no error message” means the task is still progressing
- letting a failed target pause the whole batch
