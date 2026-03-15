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
  runs/
  artifacts/
  tasks/
```

## Storage split

- Google Sheet => index, status, review, queueing
- Local playbook files => full step-by-step memory
- Local task store => recoverable execution state, checkpoints, errors, and locks
- Secrets store => passwords and sensitive tokens

## Why task state lives next to playbooks

Playbooks capture how a site can be handled.
Task state captures what happened on this specific attempt.

They should live near each other so the system can:
- recover after crashes or timeouts
- preserve evidence from failed attempts
- update playbooks from successful or partially successful runs

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
- `entrypoints`
- `steps`
- `success_signals`
- `failure_signals`
- `manual_touchpoints`
- `notes`

Each step should ideally record:
- `step_index`
- `action_type`
- `goal`
- `locator_primary`
- `locator_fallback`
- `input_source`
- `success_signal`
- `failure_signal`
- `notes`

## Pattern playbooks

Create a pattern playbook only after multiple similar sites succeed.

Use `scope=pattern` for families such as:
- `google-oauth-directory`
- `email-signup-directory`

## Learning rules

- Update/create a site playbook whenever a run achieves a reusable success path.
- Do not promote one noisy success into a pattern playbook immediately.
- Promote only after 2-3 similar successes with a recognizably similar structure.
- Treat failed runs as heuristics too: add negative notes when they help avoid repeated dead ends.
- When a task fails after reaching a meaningful internal phase, save the artifact and checkpoint so later workers do not rediscover the same path blindly.

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
- `notes`

## Credential policy

- Store `credential_ref` in playbooks and Sheet indexes.
- Store real passwords only in a secure local secret store.
- Never embed passwords in the playbook body.
