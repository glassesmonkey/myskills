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

## v1 action matrix

### Directory / launch platform
- `google_oauth` + standard form => preferred v1 path
- `email_signup` + email verification => allowed v1 path
- `none` + standard form => allowed v1 path
- payment/backlink/phone verification => `NEEDS_HUMAN`
- CAPTCHA/Cloudflare walls => usually `NEEDS_HUMAN`

### Community / forum
- classify the surface
- look for profile-link, showcase, or self-promo areas
- do not auto-produce long posts in v1
- default to `NEEDS_HUMAN` when content strategy matters

### Article platform
- identify whether it is a genuine writing surface or just a listing surface
- do not auto-publish long-form content in v1
- route toward `NEEDS_HUMAN` unless a later version explicitly supports that platform

## Browser choice

Use built-in browser control for:
- anonymous scouting
- public page discovery
- quick inspection of forms and links

Use Browser Relay for:
- Google OAuth
- authenticated sessions
- flows that depend on human browser state
- sites that break in headless or isolated contexts

## Execution routing

Preferred `strategy` values:
- `dir_google_oauth`
- `dir_email_signup`
- `dir_noauth_submit`
- `community_profile_only`
- `community_post_needed`
- `article_pitch_needed`
- `skip`

## Reuse rules

Before attempting a new site:
1. scout enough to fingerprint the platform
2. compare against known site or pattern playbooks
3. reuse only when the confidence is high enough

Suggested confidence handling:
- `>= 0.85` => reuse directly
- `0.60 - 0.84` => semi-automatic attempt with extra observation
- `< 0.60` => do full scouting and avoid direct playbook reuse
