# Product Profiler

## Goal

Build a factual, reusable profile for the promoted site before writing submissions or proposing article angles.

Read `references/init-intake.md` first when setting up a new run or when a running campaign keeps stalling on missing company facts, emails, or policy choices.

## Source order

Prefer sources in this order:
1. explicit user instructions
2. approved init-intake answers
3. official homepage / landing page
4. pricing / feature / docs / about pages
5. existing project research documents provided by the user
6. only then infer cautiously from the site itself

## Profile sections

### Required marketing/content fields
- `product_name`
- `canonical_url`
- `category_primary`
- `category_secondary`
- `one_liner`
- `short_description`
- `medium_description`
- `core_features`
- `use_cases`
- `target_audience`
- `pricing_model`
- `differentiators`
- `safe_claims`
- `not_supported`
- `directory_angles`
- `community_angles`
- `article_angles`

### Required submission-ops fields
Persist these too when available from init intake:
- `company_name`
- `based_in_city`
- `based_in_region`
- `based_in_country`
- `founded_year`
- `launch_date`
- `team_size`
- `funding_status`
- `revenue_stage`
- `mrr_disclosure`
- `submitter_name`
- `submitter_first_name`
- `submitter_last_name`
- `submitter_phone`
- `primary_email`
- `company_email`
- `personal_fallback_email`
- `founder_name`
- `markets`

### Required policy fields
Capture boundaries that affect automation decisions:
- `allow_gmail_signup`
- `allow_company_email_signup`
- `preferred_verification_email`
- `preferred_auth_order`
- `allow_site_account_reuse`
- `allow_mrr_disclosure`
- `allow_founder_identity_disclosure`
- `allow_phone_address_disclosure`
- `allow_oauth_login`
- `allow_manual_browser`
- `allow_paid_listing`
- `allow_reciprocal_backlink`

## Claim-safe rules

- Do not invent unsupported features.
- Keep claims tied to visible evidence or explicit user confirmation.
- Keep a `not_supported` list to avoid drift.
- If a capability is uncertain, flag it instead of writing through uncertainty.
- Do not conflate funding status with revenue stage.
- Do not infer MRR disclosure permission from the existence of revenue.
- Prefer normalized values for execution, but retain the user's raw wording when that nuance may matter later.

## Output usage

### Directory submissions
Use:
- `one_liner`
- `short_description`
- `category_primary`
- `canonical_url` or campaign UTM URL
- any required ops fields such as location, founded year, team size, and submitter identity

### Community introductions
Use:
- `target_audience`
- `use_cases`
- a low-hype angle from `community_angles`

### Article / UGC ideas
Use:
- `article_angles`
- `safe_claims`
- `differentiators`

### Signup / verification flows
Use:
- the preferred email hierarchy from the profile
- the disclosure-policy fields before submitting phone, founder identity, revenue, or OAuth scopes

## Persistence

Store the full profile locally under `data/web-backlinker/product-profiles/`.
Mirror a human-readable summary into the `ProductProfile` tab.
If the run is still `WAITING_CONFIG`, persist the partial profile anyway so later updates become additive instead of re-discovery work.
