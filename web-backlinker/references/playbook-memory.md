# Playbook Memory

## Canonical storage

Keep playbook bodies locally, not in Google Sheet.

Recommended runtime layout:

```text
data/web-backlinker/
  playbooks/
    sites/
    patterns/
  product-profiles/
  accounts/
  runs/
  artifacts/
  tasks/
  submission-ledger.json
```

## Storage split

- Google Sheet => index, status, review, queueing
- Local playbook files => full step-by-step memory
- Local task store => recoverable execution state, checkpoints, errors, and locks
- Local account registry => reusable per-domain signup/login metadata
- Local submission ledger => campaign-wide memory of which promoted site already reached submit/listed states on which target
- Secrets store => passwords and sensitive tokens

## Why task state lives next to playbooks

Playbooks capture how a site can be handled.
Task state captures what happened on this specific attempt.
The submission ledger captures whether this promoted site has already been submitted or listed on this target across runs.
The account registry captures whether the target already has a reusable site account.

They should live near each other so the system can:
- recover after crashes or timeouts
- preserve evidence from failed attempts
- update playbooks from successful or partially successful runs
- stop later runs from resubmitting the same target blindly
- stop later runs from re-registering the same target account blindly

## Site playbook schema

A site playbook should capture:
- `playbook_id`
- `scope` (`site`)
- `domain`
- `site_type`
- `auth_type`
- `submission_type`
- `version`
- `success_count`
- `credential_ref`
- `account_ref`
- `browser_profile_ref`
- `entrypoints`
- `steps`
- `direct_steps`
- `field_map`
- `result_checks`
- `execution_mode`
- `automation_disposition`
- `stability_score`
- `replay_confidence`
- `last_validated_at`
- `success_signals`
- `failure_signals`
- `manual_touchpoints`
- `fallback_route`
- `notes`

Each remembered step should ideally record:
- `step_index`
- `action_type`
- `goal`
- `locator_primary`
- `locator_fallback`
- `input_source`
- `success_signal`
- `failure_signal`
- `notes`

Each `direct_step` should ideally record:
- `step_index`
- `action_type`
- `goal`
- `target` / `selector` / `url`
- `input_source` or literal `value`
- `success_signal`
- `failure_signal`
- `notes`

## Pattern playbooks

Create a pattern playbook only after multiple similar sites succeed.

Use `scope=pattern` for families such as:
- `email-signup-directory`
- `noauth-directory`
- `google-oauth-directory`

## Account registry schema

Prefer at least:
- `domain`
- `account_ref`
- `auth_type`
- `signup_email`
- `username`
- `credential_ref`
- `browser_profile_ref`
- `created_at`
- `last_verified_at`
- `status`
- `notes`

## Learning rules

- Update/create a site playbook whenever a run achieves a reusable success path.
- Do not promote one noisy success into a pattern playbook immediately.
- Promote only after 2-3 similar successes with a recognizably similar structure.
- Treat failed runs as heuristics too: add negative notes when they help avoid repeated dead ends.
- When a task fails after reaching a meaningful internal phase, save the artifact and checkpoint so later workers do not rediscover the same path blindly.
- When a site account is created or verified, update the account registry immediately.
- When a site is reused successfully, increase `stability_score` / `replay_confidence` instead of only adding prose notes.

## Task-store recommendations

Keep a recoverable task store under `data/web-backlinker/tasks/`.

Suggested files:
- `current-run.json` — canonical task array for the active run
- `events.jsonl` — append-only state-change and checkpoint log

Each task should capture at least:
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
- `execution_mode`
- `automation_disposition`
- `playbook_confidence`
- `replay_status`
- `account_ref`
- `credential_ref`
- `notes`

## Credential policy

- Store `credential_ref` in playbooks, task state, and Sheet indexes when needed.
- Store raw passwords only in a secure local secret store.
- Never embed passwords in the playbook body.
- Never place raw passwords into the account registry.
