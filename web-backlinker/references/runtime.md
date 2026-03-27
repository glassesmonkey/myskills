# Runtime

## End-To-End Flow

1. Bootstrap runtime storage with `scripts/bootstrap_runtime.py`.
2. Probe the promoted site with `scripts/probe_promoted_site.py`.
3. Initialize intake with `scripts/init_intake.py`.
4. If the manifest is `WAITING_CONFIG`, stop immediately and ask the operator for the missing fields before any target-site scouting, browser execution, signup, or submission.
5. Import the target list with `scripts/task_store.py init`.
6. Claim one task with `scripts/task_store.py claim`.
7. Inspect target-site memory:
   - exact site playbook
   - reusable account
   - prior submission ledger match
8. If memory is insufficient, scout only as much as needed with `scripts/scout_target.py`.
9. Classify:
   - site type
   - auth type
   - anti-bot level
   - likely submit path
10. If the site is new but promising, scaffold a first-pass playbook with `scripts/scaffold_playbook.py`.
11. Build a compact execution brief with `scripts/prepare_worker_brief.py`.
12. Choose a route with `scripts/select_execution_plan.py`.
13. Execute or park the row.
14. Persist the outcome, then claim the next row.

## Why One Row At A Time

The point is not slowness. The point is recoverability.

One target row can involve:

- signup
- email verification
- profile completion
- a delayed moderation confirmation

If that row fails halfway through, only that row should need recovery.

## Recommended Status Meanings

- `READY`: not started or ready again
- `RUNNING`: currently claimed
- `WAITING_EMAIL`: waiting for a mailbox step
- `WAITING_HUMAN`: worth doing, but a human credential or decision is missing
- `RETRYABLE`: retry later
- `DONE`: successfully submitted or verified
- `SKIPPED`: terminal skip

## Worker Rules

- Claim one task at a time.
- Checkpoint after every meaningful phase change.
- Keep notes short and factual.
- When a row is blocked, park it and move on.
- Do not ask the user after every row.

## What Counts As A Meaningful Checkpoint

- discovered login requirement
- detected email-signup path
- reused existing account
- found verification email
- clicked verification link
- form submitted
- moderation pending
- blocker detected and row parked

## When To Mark The Whole Run As Waiting

Use a run-level wait only when the whole campaign cannot proceed safely, for example:

- promoted-site profile is too incomplete to write truthful submissions
- `gog` is required for the selected route but is not configured
- browser automation is unavailable

When the run is `WAITING_CONFIG`, the correct next action is to ask for the missing intake fields, not to keep exploring submission targets.

## Retry Rules

- Retry transient site failures later.
- Do not retry the same anti-bot wall in a loop.
- Do not reopen a known-success site in full-discovery mode when a validated playbook exists.
