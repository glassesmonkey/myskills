# Account Registry

## Goal

Reuse site accounts instead of re-registering on every campaign or every promoted-site submission.

## Core split

Keep account data in three layers:

1. **Playbook**
   - stores `account_ref` / `credential_ref` / `browser_profile_ref`
   - does not store raw passwords

2. **Account registry**
   - local metadata for site accounts
   - keyed by target domain

3. **Secret storage**
   - raw passwords or app passwords
   - never store these in Sheet, plain playbooks, or normal notes/logs

## Recommended storage

```text
data/web-backlinker/
  accounts/
    site-accounts.json
```

## Registry fields

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

## Default policy

- Prefer **one reusable account per target domain** unless the site clearly requires otherwise.
- Prefer email signup over OAuth when both are allowed and the email route is not materially worse.
- Reuse the same site account for later promoted-site submissions whenever safe.

## Auth preference order

Prefer this order unless the site strongly favors a different route:
1. no-auth submit
2. email signup + password
3. Google OAuth fallback
4. magic link / email-code flows
5. human-only flows

## Status values

Suggested statuses:
- `active`
- `needs_reauth`
- `blocked`
- `deprecated`
- `oauth_only`

## Update rules

- Update `last_verified_at` after a confirmed successful login or submission using that account.
- Mark `needs_reauth` when login breaks but the site is still worth keeping.
- Mark `deprecated` when the site no longer matters or the account should no longer be reused.

## Safety

- Never store raw passwords in the registry.
- Never store passwords in Sheet.
- Never log raw secrets in artifacts or event logs.
- Prefer `credential_ref` values that point to secure local secret storage.
