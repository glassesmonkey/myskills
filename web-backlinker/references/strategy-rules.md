# Strategy Rules

## Site classification

Prefer one `site_type` from:
- `directory`
- `launch_platform`
- `community`
- `forum`
- `article_platform`
- `unknown`

Useful signals:
- `submit tool`, `add listing`, `list your product` => likely `directory`
- `launch`, `product of the day`, `ship` => likely `launch_platform`
- `new topic`, `reply`, `showcase`, `introduce yourself` => likely `community` or `forum`
- `write`, `publish story`, `editor`, `draft` => likely `article_platform`

## Auth classification

Prefer one `auth_type` from:
- `google_oauth`
- `email_signup`
- `magic_link`
- `none`
- `unknown`

## Auth preference order

When multiple auth paths are available, prefer this order unless the site strongly favors a different route:
1. `none`
2. `email_signup`
3. `google_oauth`
4. `magic_link`
5. human-only/manual

Interpretation:
- prefer reusable email-signup accounts when email and OAuth are both viable and the email route is not materially worse
- do not force email signup when the email route is clearly more fragile or more manual than standard Google OAuth

## v1 action matrix

### Directory / launch platform
- `none` + standard form => preferred v1 path
- `email_signup` + standard verification => allowed v1 path
- `google_oauth` + standard form => allowed, but not a default fast-path candidate in v1
- payment / phone verification => `REJECT` for auto-execution
- reciprocal backlink / link exchange => `ASSISTED_EXECUTE` for later manual review; record but do not proactively submit
- CAPTCHA/Cloudflare walls => usually `ASSISTED_EXECUTE` or `DEFER_RETRY`, not automatic fast path

### Community / forum
- classify the surface
- look for profile-link, showcase, or self-promo areas
- do not auto-produce long posts in v1
- default to `ASSISTED_EXECUTE` or `REJECT` when content strategy matters

### Article platform
- identify whether it is a genuine writing surface or just a listing surface
- do not auto-publish long-form content in v1
- route toward `ASSISTED_EXECUTE` or `REJECT` unless a later version explicitly supports that platform

## Automation disposition

Do not treat every non-auto row as a hard rejection. Prefer one disposition:
- `AUTO_EXECUTE` — safe and stable enough for automatic execution
- `ASSISTED_EXECUTE` — worth pursuing, but likely needs human help or approval
- `DEFER_RETRY` — not executable now, but should be retried later
- `REJECT` — not worth executing under current policy or quality standards

## Browser / executor choice

### Use built-in browser control for:
- anonymous scouting
- public page discovery
- first-pass inspection of forms and links
- new sites that do not yet have a stable playbook

### Use Browser Relay for:
- Google OAuth
- authenticated sessions
- flows that depend on human browser state
- sites that break in headless or isolated contexts

### Use `browser_use_direct` for:
- stable directories or launch/listing forms
- sites with replayable submit steps
- sites with clear success/failure signals
- sites likely to be reused across campaigns

## Execution routing

Preferred `strategy` values:
- `dir_noauth_submit`
- `dir_email_signup`
- `dir_google_oauth`
- `community_profile_only`
- `community_post_needed`
- `article_pitch_needed`
- `skip`

Preferred `execution_mode` values:
- `native_scout`
- `native_submit`
- `browser_use_direct_observe`
- `browser_use_direct`
- `relay_auth`
- `manual`

## Fast-path promotion rules

Promote a site into `browser_use_direct` only when:
- the site has a successful scout path
- a site playbook exists with `direct_steps`
- replay has succeeded at least once
- the site has clear `result_checks` and fallback route
- the site looks likely to be reused enough to justify compile cost

Suggested confidence handling:
- `>= 0.85` => reuse directly (`browser_use_direct`)
- `0.60 - 0.84` => `browser_use_direct_observe` or `native_submit`
- `< 0.60` => full scouting; do not trust direct replay yet

## Reuse rules

Before attempting a new site:
1. scout enough to fingerprint the platform
2. compare against known site or pattern playbooks
3. check the account registry for an existing per-domain account
4. reuse only when the confidence is high enough

Before registering a new site account:
1. verify no reusable account already exists for the target domain
2. prefer email signup over OAuth when practical
3. store only `account_ref` / `credential_ref` / `browser_profile_ref` in playbooks and task state
