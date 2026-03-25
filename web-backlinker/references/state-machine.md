# State Machine

## Row states (Sheet-facing)

- `IMPORTED` — normalized row exists in `Targets`
- `SCOUTED` — reconnaissance completed but no route chosen yet
- `READY_AUTO` — safe/in-scope to execute automatically
- `READY_SEMI` — executable with likely human touchpoints but still worth attempting
- `RUNNING` — actively being processed
- `PENDING_EMAIL` — submission progressed; waiting for email verification or follow-up mail
- `SUBMITTED` — submitted successfully for this run
- `VERIFIED` — email verification or similar follow-up completed
- `NEEDS_HUMAN` — requires human action; batch must continue
- `SKIPPED` — intentionally not pursued in this run
- `FAILED` — execution failed and did not produce a usable result

## Local task states (task-store facing)

- `PENDING` — not yet claimed by a worker
- `SCOUTING` — worker is gathering route/obstacle data
- `READY` — executable when the dispatcher chooses it
- `RUNNING` — worker currently owns the task
- `WAITING_EMAIL` — blocked on verification email or delayed follow-up
- `WAITING_HUMAN` — blocked on human-required action
- `DONE` — finished successfully
- `FAILED` — failed for now; may be retryable
- `RETRYABLE` — safe to retry later
- `STALLED` — no progress for too long; watchdog should decide recovery
- `SKIPPED` — intentionally excluded from further execution

## Run states

- `BOOTSTRAPPED`
- `WAITING_CONFIG`
- `SHEET_CREATED`
- `IMPORTED`
- `SCOUTING`
- `EXECUTING`
- `RESUMING`
- `HALTED`
- `COMPLETED`

## Lease states

- `ACTIVE` — one worker currently owns the batch drain lease
- `RELEASED` — no active owner
- `EXPIRED` — logical state used by watchdog when the stored `expires_at` is already in the past

## Task metadata fields

Prefer compact machine-friendly fields alongside human notes:
- `reason_code`
- `route`
- `execution_mode`
- `automation_disposition`
- `playbook_confidence`
- `replay_status`
- `account_ref`
- `credential_ref`
- `artifact_ref`
- `sheet_status`
- `sheet_note`
- `result_code`

Useful `reason_code` examples include `already_submitted`, `captcha_required`, `cloudflare_challenge`, `payment_required`, and `manual_content_needed`.

Use short code-first values in the durable state. Expand into human prose only when reporting outward.

## Automation disposition values

These are not replacements for task states. They describe execution intent:
- `AUTO_EXECUTE`
- `ASSISTED_EXECUTE`
- `DEFER_RETRY`
- `REJECT`

## Execution mode values

Use one of:
- `native_scout`
- `native_submit`
- `browser_use_direct_observe`
- `browser_use_direct`
- `relay_auth`
- `manual`

## Replay status values

Use one of:
- `not_compiled`
- `compiled`
- `observe`
- `validated`
- `invalidated`

## Task phases

Use a lightweight phase string to indicate where the worker is inside a long task, for example:
- `config.collect`
- `config.normalize`
- `scout.homepage`
- `scout.submit-path`
- `signup.start`
- `signup.submit`
- `email.wait`
- `email.verify`
- `submit.form`
- `submit.upload`
- `submit.final`
- `postsubmit.review`
- `playbook.compile`
- `playbook.replay-validate`

A worker run may process up to 3 rows, but each active row should still checkpoint phase progress every 60-120 seconds.

## Allowed row transitions

- `IMPORTED -> SCOUTED`
- `SCOUTED -> READY_AUTO`
- `SCOUTED -> READY_SEMI`
- `SCOUTED -> NEEDS_HUMAN`
- `SCOUTED -> SKIPPED`
- `IMPORTED -> SKIPPED` when a cross-run submission-ledger match proves the promoted site was already submitted/listed on that target
- `READY_AUTO -> RUNNING`
- `READY_SEMI -> RUNNING`
- `RUNNING -> SUBMITTED`
- `RUNNING -> PENDING_EMAIL`
- `RUNNING -> NEEDS_HUMAN`
- `RUNNING -> SKIPPED`
- `RUNNING -> FAILED`
- `PENDING_EMAIL -> VERIFIED`
- `PENDING_EMAIL -> NEEDS_HUMAN`
- `PENDING_EMAIL -> FAILED`
- `FAILED -> READY_SEMI` (when a retry is explicitly approved)
- `NEEDS_HUMAN -> READY_SEMI` (after a human clears the blocker)

## Allowed task transitions

- `PENDING -> SCOUTING`
- `SCOUTING -> READY`
- `SCOUTING -> WAITING_HUMAN`
- `SCOUTING -> SKIPPED`
- `READY -> RUNNING`
- `RUNNING -> WAITING_EMAIL`
- `RUNNING -> WAITING_HUMAN`
- `RUNNING -> DONE`
- `RUNNING -> FAILED`
- `RUNNING -> STALLED`
- `WAITING_EMAIL -> RUNNING`
- `WAITING_EMAIL -> WAITING_HUMAN`
- `WAITING_EMAIL -> DONE`
- `FAILED -> RETRYABLE`
- `RETRYABLE -> RUNNING`
- `STALLED -> RETRYABLE`
- `WAITING_HUMAN -> READY` (after human clears blocker)

## Manual reason codes

Prefer one of:
- `captcha`
- `captcha_required`
- `cloudflare_challenge`
- `payment_required`
- `backlink_required`
- `phone_verification`
- `suspicious_site`
- `oauth_scope_review`
- `manual_content_needed`
- `missing_config`
- `unknown_flow`
- `login_failed`
- `site_error`
- `scope_mismatch`

Interpretation note:
- `backlink_required` means “record for later exchange-link review”, not “auto-accept now” and not necessarily “permanent reject”. Prefer a human-review queue / assisted path.

## Transition rules

- Human blockers are row-level only.
- Infrastructure failures are run-level and may justify `[WB-HALT]`.
- `PENDING_EMAIL` / `WAITING_EMAIL` should not block the batch; resume later.
- `READY_SEMI` should still be attempted if it stays within v1 safety rules.
- A task may be long-lived, but it must emit progress checkpoints regularly.
- Watchdog should mark a task `STALLED` only when the task has exceeded the no-progress threshold, not merely because the total task runtime is long.
- `WAITING_CONFIG` is run-level: it means setup is incomplete, not that a single row failed.
- While the run is `WAITING_CONFIG`, workers may do setup and light scouting but must not perform external-write steps such as signup, submission, ownership claim, or verification.
- The batch lease protects the run-level drain loop; row locks still protect per-row ownership.
- Prefer compact `recent_notes` in the run manifest over an ever-growing `notes` history. Full detail belongs in `events.jsonl` and artifacts.
