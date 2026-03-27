# Init Intake

## Goal

Collect the promoted-site facts, submission identities, and policy boundaries before the first real submission worker runs.

The point is simple:

- do not let a worker discover halfway through that there is no approved email
- do not guess disclosure policy on a live submission form
- do not start account/signup flows when the company has not approved them

## Core rule

If required intake is incomplete:

- persist whatever is already known
- keep the run in `WAITING_CONFIG`
- allow setup and scouting only
- block real submit/signup/verify workers

## Required fields

### Product identity

- `product_name`
- `canonical_url`
- `one_liner`
- `short_description`
- `medium_description`

### Categorization

- `category_primary`
- `target_audience`
- `use_cases`

### Submission identity

- `submitter_name`
- `primary_email`
- `company_email`
- `preferred_verification_email`

### Policy boundaries

- `allow_gmail_signup`
- `allow_company_email_signup`
- `allow_oauth_login`
- `allow_manual_captcha`
- `allow_paid_listing`
- `allow_reciprocal_backlink`
- `allow_founder_identity_disclosure`
- `allow_phone_disclosure`
- `allow_address_disclosure`

## Suggested Prompt Template

Ask for the missing fields as one compact initialization payload before any target-site scouting or submission.

Prefer natural Chinese phrasing for normal users. The agent should understand answers semantically and map them back into structured fields; the script should remain the validator and store, not the user-facing UX layer.

Use this template:

- Product name:
- Canonical URL:
- Company name:
- One-liner:
- Short description:
- Medium description:
- Primary category:
- Target audience:
- Use cases:
- Submitter full name:
- Primary email:
- Company email:
- Preferred verification email:
- Allow Gmail signup: yes/no
- Allow company email signup: yes/no
- Allow OAuth login: yes/no
- Allow manual CAPTCHA / browser takeover: yes/no
- Allow paid listing: yes/no
- Allow reciprocal backlink: yes/no
- Allow founder identity disclosure: yes/no
- Allow phone disclosure: yes/no
- Allow address disclosure: yes/no

## Recommended fields

- `company_name`
- `founder_name`
- `founding_year`
- `launch_date`
- `based_in_country`
- `pricing_url`
- `privacy_url`
- `logo_url`
- `screenshot_url`
- `markets`

## Safe actions while waiting

- bootstrap runtime
- import targets
- probe the promoted site
- optionally normalize the target list

## Blocked actions while waiting

- target-site scouting that is part of a real submission run
- account creation
- login flows
- submission POSTs
- verification email clicks
- ownership claim flows

## Operator workflow

1. Run `bootstrap_runtime.py`
2. Run `probe_promoted_site.py`
3. Run `init_intake.py` with the manifest path
4. Fill missing required fields
5. Only after the manifest leaves `WAITING_CONFIG`, start `run_next.py`
