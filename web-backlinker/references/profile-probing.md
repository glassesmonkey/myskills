# Profile Probing

## Goal

Turn the promoted site URL into a reusable material pack before touching target forms.

## Source Order

Prefer:

1. explicit user input
2. official homepage
3. official pricing, features, docs, about, contact, privacy, and security pages
4. cautious inference only when the page itself supports it

## What To Collect Early

- product name
- canonical URL
- short description
- medium description
- feature bullets
- category hints
- pricing page
- trust or privacy page
- contact emails
- social links

## What To Collect Only With Evidence

- founder name
- founded year
- team size
- location
- revenue or funding details

If the official site does not clearly show these facts, leave them missing.

## Dynamic Backfill

When a later form asks for something missing:

1. map the missing field to likely official pages
2. re-run `scripts/probe_promoted_site.py` with `--need`
3. merge the refreshed profile instead of rebuilding from scratch

Useful mappings:

- `pricing_model` -> pricing page
- `company_email` -> contact page
- `trust_page` -> privacy or security page
- `about_company` -> about page

## Output Shape

The probe script should keep a JSON profile with:

- extracted facts
- source URLs
- missing fields
- timestamps

This profile is the safe source for later form filling and copy generation.
