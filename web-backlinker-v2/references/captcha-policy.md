# CAPTCHA Policy

## Goal

Do not burn time or cross the line into anti-bot escalation.

## Allowed Challenge Tiers

### `none`

Proceed normally.

### `simple_text`

Examples:

- "Type the word shown"
- "Enter the letters in the image"
- "What is 4 + 3?"

Allowed action:

- one careful attempt

### `simple_image`

Examples:

- obvious single-image word captcha
- obvious color or shape question with local page evidence

Allowed action:

- one careful attempt when the answer is directly inferable

## Stop Immediately On These

- Cloudflare challenge pages
- Turnstile
- reCAPTCHA
- hCaptcha
- managed challenge loops
- device integrity or browser fingerprint traps
- any obvious human verification gate that is not a simple local captcha

For these, record evidence and skip the row. Do not retry in the same run. Do not escalate to manual solving unless the human explicitly asks for that specific site.

## Attempt Budget

- do not loop
- do not refresh repeatedly
- do not try multiple solver strategies

One attempt is enough. If it fails, park the row.

## Parking Note Format

Keep the note factual, for example:

- `cloudflare challenge on submit page`
- `simple text captcha failed once`
- `managed anti-bot after oauth redirect`
