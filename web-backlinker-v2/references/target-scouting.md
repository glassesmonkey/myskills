# Target Scouting

## Goal

Before writing externally, reduce an unknown target site to a small structured summary.

## What To Extract

- likely site type
- likely auth type
- likely anti-bot level
- submit-related links
- visible forms and fields
- likely reusable field map

## Scouting Order

1. Inspect the given page.
2. If it is not the actual submit page, follow the strongest submit-related link.
3. Stop once the skill has enough information to classify and route the row.

## Good Enough Threshold

Do not over-scout. You have enough when you know:

- whether the row is worth auto-executing
- whether login is required
- whether advanced anti-bot is present
- which page should become the submit entrypoint

## Outputs That Matter Later

A good scout artifact should be strong enough to:

- initialize a site playbook
- build a worker brief
- decide whether to park the row

## Anti-Bot Interpretation

- `none`: proceed
- `simple_*`: one careful attempt may be acceptable
- `cloudflare`, `turnstile`, `recaptcha`, `hcaptcha`, `managed`: park
