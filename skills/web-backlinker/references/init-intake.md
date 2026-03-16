# Init Intake

## Goal

Collect the promoted-site facts, submission identities, and policy boundaries up front so the batch does not stall later on missing basics.

Use this before the first real worker run of a campaign.

## Core rule

If the required intake is incomplete:
- still allow sheet creation and target import
- persist the partial promoted-site profile locally
- mark the run `WAITING_CONFIG`
- do not start normal submission workers yet

Only move into normal execution after the required intake is filled.

## Required intake

### Product identity
- `product_name`
- `canonical_url`
- `company_name` if different from product name
- `one_liner`
- `short_description`
- `medium_description` or approved `150-300 word intro`

### Company facts
- `based_in_city`
- `based_in_region`
- `based_in_country`
- `founded_year`
- `launch_date`
- `team_size`
- `funding_status`
- `revenue_stage`
- `mrr_disclosure`
  - exact value, range, `not_disclosed`, or `pre_revenue`

### Categorization
- `category_primary`
- `category_secondary`
- `markets` / tags
- `target_audience`
- `use_cases`

### Submission identity
- `submitter_name`
- `submitter_first_name`
- `submitter_last_name`
- `submitter_phone`
- `primary_email`
- `company_email`
- `personal_fallback_email`
- `founder_name` when public founder identity may be needed

### Policy boundaries
- whether Gmail signup is allowed
- whether company-domain email signup is allowed
- preferred company email for verification / claim flows
- whether MRR may be disclosed
- whether founder identity may be disclosed
- whether phone/address may be disclosed
- whether OAuth login is allowed
- whether manual browser / CAPTCHA completion is allowed
- whether paid listings are allowed
- whether reciprocal-backlink listings are allowed

## Recommended intake

Collect these when available because they unblock many directories later:
- logo path or URL
- screenshot path or URL
- pricing page URL
- privacy/security page URL
- social links
- ZIP/address
- founder title
- disclosure rule for traffic/download counts
- disclosure rule for tech stack

## Suggested prompt template

Ask for a compact initialization payload before starting the real run:

- Product name:
- Canonical URL:
- Company name:
- One-liner:
- Short description:
- 150-300 word intro:
- Based in city:
- Based in region/state:
- Based in country:
- Founded year:
- Launch date:
- Team size:
- Funding:
- Revenue stage:
- MRR:
- Primary category:
- Secondary category:
- Markets/tags:
- Target audience:
- Use cases:
- Submitter full name:
- Submitter phone:
- Primary email:
- Company-domain email:
- Personal fallback email:
- Founder name:
- Allow Gmail signup: yes/no
- Allow company email signup: yes/no
- Preferred verification email:
- Allow MRR disclosure: yes/no
- Allow founder identity disclosure: yes/no
- Allow phone/address disclosure: yes/no
- Allow OAuth login: yes/no
- Allow CAPTCHA/manual browser: yes/no
- Allow paid listing: yes/no
- Allow reciprocal backlink: yes/no

## Normalization rules

Normalize user answers into profile-friendly values:
- expand country/state names when obvious
- map funding answers like "none" to `Bootstrapped / no external funding`
- map revenue-stage answers like "not funded" separately from funding status; do not conflate them
- split submitter full name into first/last when safe
- preserve both raw user wording and normalized value when the wording matters

## Execution gating

### Safe to proceed before full intake
These can still happen while `WAITING_CONFIG`:
- create the run manifest
- create the Google Sheet
- import and dedupe targets
- perform light scouting that does not write externally
- build a partial promoted-site profile

### Do not proceed before full intake
Do not do these until required intake is complete:
- account signup
- submission POSTs
- email verification steps
- profile claim/ownership flows
- any row that would force guessing company facts, contact identity, or disclosure policy

## Resume behavior

When missing fields are later supplied:
- update the local promoted-site profile first
- record the new values in memory/playbook notes if they are likely reusable
- change the run from `WAITING_CONFIG` to `EXECUTING`
- then resume workers normally
