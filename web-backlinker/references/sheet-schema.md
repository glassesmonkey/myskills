# Google Sheet Schema

This skill treats Google Sheet as the operational control panel. It is not the canonical playbook store.

## Tabs

### 1. Config
Campaign-level settings.

Required columns:
- `campaign_name`
- `promoted_url`
- `product_name`
- `contact_email`
- `registration_email`
- `allow_paid_submission`
- `allow_reciprocal_backlink`
- `default_utm_template`
- `run_mode`
- `notes`

Notes:
- If `promoted_url` or `product_name` is missing, the run may continue only in setup/scout mode.
- Do not store passwords here.

### 2. ProductProfile
Review-friendly summary of the promoted-site profile.

Required columns:
- `product_name`
- `canonical_url`
- `category_primary`
- `category_secondary`
- `one_liner`
- `short_description`
- `core_features`
- `target_audience`
- `pricing_model`
- `differentiators`
- `safe_claims`
- `not_supported`
- `directory_angles`
- `community_angles`
- `article_angles`

### 3. Targets
Main row-level control table. One target URL per row.

Required columns:
- `row_id`
- `input_url`
- `normalized_url`
- `domain`
- `site_name`
- `site_type`
- `submit_url`
- `login_url`
- `signup_url`
- `publish_url`
- `auth_type`
- `needs_account`
- `needs_email_verification`
- `has_captcha`
- `has_cloudflare`
- `requires_payment`
- `requires_backlink`
- `requires_manual_content`
- `strategy`
- `automation_level`
- `matched_playbook_id`
- `playbook_confidence`
- `status`
- `manual_reason`
- `next_action`
- `attempt_count`
- `last_run_id`
- `last_attempt_at`
- `priority`
- `decision`
- `human_notes`

### 4. Runs
Batch-level summary.

Required columns:
- `run_id`
- `started_at`
- `ended_at`
- `mode`
- `total_targets`
- `submitted_count`
- `verified_count`
- `pending_email_count`
- `needs_human_count`
- `skipped_count`
- `failed_count`
- `summary`

### 5. Events
Append-only, low-volume event log. Keep it coarse-grained.

Required columns:
- `ts`
- `run_id`
- `row_id`
- `domain`
- `stage`
- `event`
- `message`
- `artifact_ref`

Write only at meaningful checkpoints, not for every click.

### 6. PlaybooksIndex
Sheet-side index for local playbooks.

Required columns:
- `playbook_id`
- `scope`
- `domain_or_family`
- `site_type`
- `auth_type`
- `submission_type`
- `version`
- `success_count`
- `last_success_at`
- `confidence`
- `credential_ref`
- `playbook_path`
- `active`

## Write policy

Allowed write points:
- after sheet creation
- after target import
- after row scouting completes
- after row execution reaches a terminal state for the run
- after email verification status changes
- at run completion

Avoid:
- per-click writes
- per-field-input writes
- noisy telemetry that makes the sheet unreadable
