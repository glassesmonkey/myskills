# Hacker News posting policy

## Goal
Post quickly, but keep credibility high enough that the HN account does not become a rumor cannon.

## Confidence tiers

### A-tier: rumor / early signal
Examples:
- single leak account
- single screenshot
- single UI hint
- one unexplained model ID

Action:
- ingest into local state
- do **not** auto-post to HN
- keep watching for corroboration

### B-tier: semi-confirmed
Examples:
- two independent non-official signals
- leak + OpenRouter listing
- leak + Hugging Face model card
- leak + GitHub release/readme update
- official X post without full blog/docs, but with concrete product evidence

Action:
- eligible for auto-post if the item is novel and has a canonical link worth submitting
- prefer the most stable source URL available

### C-tier: official confirmed
Examples:
- official blog post
- official docs/changelog/API release notes
- official X post with clear release statement and no stronger canonical page yet

Action:
- auto-post if not already submitted

## What link to submit

Prefer in this order:
1. official blog / docs / changelog
2. official product page / API docs
3. official X post only when no better canonical page exists yet
4. Hugging Face / GitHub only for genuinely open-source-first launches

Avoid submitting secondary commentary when a primary source exists.

## HN dedupe rules

Before posting, check:
1. local persistent DB
2. Algolia HN search for URL match
3. Algolia HN search for close title match

If an equivalent submission already exists, mark local item as `duplicate` or `posted_elsewhere` and skip.

## HN title rules

Write titles like a normal HN submitter:
- `OpenAI launches GPT-5.4 mini and nano`
- `Qwen releases Qwen 3.5 small model series`
- `xAI adds Grok text-to-speech API`

Avoid hype titles:
- `OpenAI just dropped a crazy new model`
- `This insane AI model changes everything`

Prefer:
- vendor + action + model / product
- short, factual, source-like

## Posting rate limits

Use soft limits to avoid looking spammy:
- max 3 submissions per rolling 24 hours
- first 2 monitor runs are **seed-only bootstrap runs**: ingest and classify, but do not auto-post
- only auto-post items seen within the recent lookback window (default 96h)
- if several links cover the same release wave, pick the best canonical one
- if uncertain, queue instead of posting

## Browser / session rules

The user already has Hacker News login state in Chrome. For automation:
- prefer the configured browser profile from the skill config
- if browser login state is unavailable, do not guess or force a login flow blindly
- leave the item queued and try again later

## Submission flow

Use `https://news.ycombinator.com/submitlink`.
If logged in, the page exposes a simple title/url form. Submit link posts, not `Show HN`, unless the user explicitly wants `Show HN` for their own product.
