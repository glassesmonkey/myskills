# Safety Rules

Read this file before any signup, submission, or credential-handling flow.

## Hard stops for the current row

Mark `NEEDS_HUMAN` and continue the batch when a row requires:
- payment or card entry
- reciprocal backlink acceptance
- phone verification / SMS OTP
- suspicious or excessive OAuth scopes
- CAPTCHA or Cloudflare challenge that needs a human
- long-form manual content creation
- sensitive company/person data not already approved by the user

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

## Operational quality

- Prefer fewer high-quality writes over noisy row churn.
- Leave evidence: save screenshots, HTML, or concise notes when they materially help reuse.
- Keep runs resumable: update row status before moving on.
