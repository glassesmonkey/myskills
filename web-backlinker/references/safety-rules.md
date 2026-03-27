# Safety Rules

Read this file before any signup, submission, or credential-handling flow.

## Hard stops for the current row

Mark `NEEDS_HUMAN`, `DEFER_RETRY`, or `REJECT` and continue the batch when a row requires:
- payment or card entry
- reciprocal backlink acceptance
- phone verification / SMS OTP
- suspicious or excessive OAuth scopes
- CAPTCHA or Cloudflare challenge that needs a human
- long-form manual content creation
- sensitive company/person data not already approved by the user

Special rule for reciprocal-backlink / link-exchange sites:
- record them as later-review candidates
- do **not** proactively submit or auto-accept the exchange during normal execution
- keep enough evidence (URL, screenshots, concise notes, reason code) so the user can review later and choose which ones are worth trading links with

Interpretation:
- `REJECT` => not worth pursuing under current policy or quality bar
- `DEFER_RETRY` => retry later when infrastructure/timing changes
- `NEEDS_HUMAN` / `ASSISTED_EXECUTE` => worth doing, but not safely unattended

## Hard stops for the whole run

Use `[WB-HALT]` only when the system cannot safely continue, for example:
- Google Sheet cannot be created or updated at all
- browser tooling is unavailable for the required mode
- Gmail/Gog access required for the workflow is unavailable across the batch
- local runtime storage is unavailable or corrupted

## Claim safety

- Use the promoted-site profile as the source of truth.
- Do not invent features, numbers, integrations, or guarantees.
- If the promoted site is unclear, gather facts first or mark the run as waiting for config.

## Credential handling

- Never place passwords in Sheet.
- Never paste app passwords into plain logs.
- Prefer keyring / secure local secret storage.
- Keep only `credential_ref` / `account_ref` / `browser_profile_ref` in playbooks, task state, and account registry metadata.

## Auth route policy

- Prefer no-auth submit paths first.
- Prefer email signup over OAuth when both are practical and the email path is not materially worse.
- Allow OAuth fallback when the site clearly favors it and scopes look normal.
- Do not auto-accept suspicious scopes or identity-sharing requests without review.

## Operational quality

- Prefer fewer high-quality writes over noisy row churn.
- Leave evidence: save screenshots, HTML, or concise notes when they materially help reuse.
- Keep runs resumable: update row status before moving on.
- Do not label a row as permanent failure when the right label is really assisted / deferred / policy-rejected.
