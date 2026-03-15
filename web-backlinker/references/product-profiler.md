# Product Profiler

## Goal

Build a factual, reusable profile for the promoted site before writing submissions or proposing article angles.

## Source order

Prefer sources in this order:
1. explicit user instructions
2. official homepage / landing page
3. pricing / feature / docs / about pages
4. existing project research documents provided by the user
5. only then infer cautiously from the site itself

## Required fields

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

## Claim-safe rules

- Do not invent unsupported features.
- Keep claims tied to visible evidence or explicit user confirmation.
- Keep a `not_supported` list to avoid drift.
- If a capability is uncertain, flag it instead of writing through uncertainty.

## Output usage

### Directory submissions
Use:
- `one_liner`
- `short_description`
- `category_primary`
- `canonical_url` or campaign UTM URL

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

## Persistence

Store the full profile locally under `data/web-backlinker/product-profiles/`.
Mirror a human-readable summary into the `ProductProfile` tab.
