# Site Memory

## Purpose

A successful site submission should make the next run cheaper.

That means the skill should convert fresh observations into a reusable playbook instead of leaving success trapped inside the chat log.

## Storage

Site playbooks live under:

```text
data/backlink-helper/playbooks/sites/
```

Pattern playbooks live under:

```text
data/backlink-helper/playbooks/patterns/
```

## Site Playbook Schema

Prefer these fields:

- `playbook_id`
- `scope`
- `domain_or_family`
- `domain`
- `site_type`
- `auth_type`
- `submission_type`
- `entrypoints`
- `field_map`
- `steps`
- `success_signals`
- `failure_signals`
- `result_checks`
- `simple_captcha_supported`
- `anti_bot_policy`
- `execution_mode`
- `automation_disposition`
- `account_ref`
- `credential_ref`
- `browser_profile_ref`
- `mailbox_account`
- `success_count`
- `stability_score`
- `replay_confidence`
- `last_success_at`
- `updated_at`
- `notes`

## Promotion Rules

Promote an observed path into a site playbook when:

- the submission path reached a reliable internal milestone
- the field labels were readable enough to map
- the success signal was unambiguous enough to check later

Increase confidence when the same playbook succeeds again.

Suggested confidence handling:

- `>= 0.85`: direct replay is acceptable
- `0.60 - 0.84`: replay with observation
- `< 0.60`: scout again before trusting the route

## Matching Order

When a new row starts:

1. exact domain playbook
2. `www.`-stripped domain playbook
3. pattern playbook
4. fresh scouting

## Submission Ledger

The submission ledger prevents duplicate work across campaigns.

Each active record should include:

- `promoted_url`
- `promoted_domain`
- `target_domain`
- `target_normalized_url`
- `state`
- `first_seen_at`
- `updated_at`
- `run_id`
- `task_id`
- `listing_url`
- `note`

Active states are:

- `submitted`
- `pending_email`
- `verified`
- `already_listed`

If a ledger record already matches the same promoted site and target, park the row immediately instead of rediscovering the surface.
