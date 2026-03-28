# Auth And Verification

## Auth Order

Prefer this order unless the site clearly favors something else:

1. no-auth submit
2. email signup
3. Google OAuth
4. magic link
5. human-only flow

## Account Reuse

Before creating an account:

1. check the account registry
2. check the site playbook for an existing `account_ref`
3. reuse the existing account when it is still healthy

Do not create a fresh account per campaign unless the site forces that.

## Email Signup

Default email preference:

1. company-domain address from the promoted-site profile
2. approved fallback mailbox

After a successful signup:

- save the account in `scripts/account_registry.py`
- remember the chosen email address
- remember whether the site sends a link or code
- remember any stable username rule

## OAuth (Google / Facebook / similar)

OAuth is allowed when:

- the site clearly prefers it
- the scopes look normal for basic account creation or login
- the user has approved OAuth as an allowed route

When the shared browser session already has a live Google or Facebook login, treat that as a normal reusable asset instead of parking the row pre-emptively. The worker should attempt the provider button once and continue the submission flow if the site returns to a live submit surface.

OAuth is not a license to fight anti-bot systems. If OAuth is wrapped inside Cloudflare or other managed challenge layers, park the row.

## Gmail Verification Through `gog`

Use `scripts/gmail_watch.py`. It wraps these ideas:

```bash
gog gmail search -j --results-only --max 10 "from:(site.com) newer_than:2d"
gog gmail thread get -j --results-only --full <thread-id>
```

`scripts/gmail_watch.py extract` should be the default path because it:

- searches recent verification threads
- reads the full thread
- extracts likely verification links
- extracts OTP-like codes

If `gog auth status` shows the CLI is not configured, do not fake success. Mark the row or the run as waiting for configuration.

## Secrets

- Keep raw passwords out of playbooks.
- Keep raw passwords out of the account registry.
- Store only references like `credential_ref`.
- Do not log raw secrets in artifacts.
