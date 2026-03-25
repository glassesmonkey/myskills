# State Machine (v1)

## Run states

- `CREATED` — run object exists, not ready yet
- `READY` — ready to start or resume
- `RUNNING` — actively progressing
- `WAITING_EXTERNAL` — waiting on email, cooldown, polling window, or other external timing condition
- `WAITING_HUMAN` — waiting on a human action
- `STALLED` — expected progress is missing
- `HALTED_DEPENDENCY` — blocked by browser/gateway/API/session dependency failure
- `COMPLETED` — finished successfully
- `FAILED` — terminated unsuccessfully

## Key distinction

### `WAITING_EXTERNAL`
Use when the task is intentionally waiting and the wait condition is known.

### `STALLED`
Use when progress should have continued but did not.

### `HALTED_DEPENDENCY`
Use when the root blocker is not the task logic but a dependency outage, for example:
- browser timeout
- gateway unavailable
- relay/session lost
- required API unavailable

## Allowed transitions

- `CREATED -> READY`
- `READY -> RUNNING`
- `RUNNING -> WAITING_EXTERNAL`
- `RUNNING -> WAITING_HUMAN`
- `RUNNING -> STALLED`
- `RUNNING -> HALTED_DEPENDENCY`
- `RUNNING -> COMPLETED`
- `RUNNING -> FAILED`
- `WAITING_EXTERNAL -> READY`
- `WAITING_HUMAN -> READY`
- `STALLED -> READY`
- `HALTED_DEPENDENCY -> READY`

## Reason codes (starter set)

- `tool_timeout`
- `executor_dead`
- `dependency_unavailable`
- `browser_gateway_timeout`
- `waiting_email`
- `waiting_cooldown`
- `manual_action_required`
- `missing_config`
- `site_error`
- `unknown_flow`
- `scope_mismatch`
- `completed`
