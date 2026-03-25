---
name: model-news-hn-monitor
description: Monitor new foundation-model / AI-model release signals across leak accounts, official X/blog/docs feeds, Hugging Face, GitHub, and distribution platforms; persist local state for dedupe; classify signals into rumor/semi/official; set up cron-based monitoring; and submit eligible canonical links to Hacker News using the user's logged-in browser state. Use when building or operating an automated “monitor new models and post to HN first” workflow, when checking whether a release was already seen/posted, or when configuring recurring monitoring and HN submission logic.
---

# model-news-hn-monitor

Run a fast-but-relatively-credible monitoring loop for new model releases, with local persistence and HN submission.

## Core workflow

1. **Scan multiple source layers**, not one source.
2. **Persist every signal locally** so future runs can dedupe and accumulate confidence.
3. **Classify each item** as rumor / semi / official.
4. **Auto-post only semi-confirmed or official items** that pass dedupe and HN-worthiness checks.
5. **Use bootstrap safety** on first runs so old items are seeded into the DB without getting mass-posted.
6. **Use the best canonical source URL** available at the moment of submission.

This skill is built for the user's principle: **兼听则明，偏听则暗**.

## Read these references when needed

- Read `{baseDir}/references/source-map.md` when choosing which sources to scan.
- Read `{baseDir}/references/hn-posting-policy.md` before deciding whether to auto-post and how to title the submission.

## Local persistence: required, not optional

Use the local SQLite state DB at:
- `/home/gc/.openclaw/workspace/data/model-news-hn-monitor/state.sqlite3`

Config file:
- `/home/gc/.openclaw/workspace/data/model-news-hn-monitor/config.json`

Before first use, initialize the DB:

```bash
python3 {baseDir}/scripts/state_db.py init \
  --db /home/gc/.openclaw/workspace/data/model-news-hn-monitor/state.sqlite3
```

Every signal you find must be ingested into the DB, so later runs can answer:
- have we already seen this model?
- how many independent signals do we have?
- is it already posted to HN?
- is it ready to post now?

## Bootstrap safety: prevent first-run spam

Before each scheduled monitoring cycle, call:

```bash
python3 {baseDir}/scripts/state_db.py tick-monitor \
  --db /home/gc/.openclaw/workspace/data/model-news-hn-monitor/state.sqlite3 \
  --seed-only-runs 2
```

Interpretation:
- if `bootstrap_mode=true`, ingest and classify signals **only**; do not auto-post anything yet
- only after bootstrap ends may the monitor consider auto-posting

This prevents the first run from treating already-existing recent announcements as if they were all brand new HN opportunities.

## State operations

### Ingest a signal

```bash
python3 {baseDir}/scripts/state_db.py ingest \
  --db /home/gc/.openclaw/workspace/data/model-news-hn-monitor/state.sqlite3 \
  --title "OpenAI launches GPT-5.4 mini and nano" \
  --vendor "OpenAI" \
  --model-name "GPT-5.4 mini" \
  --source-kind x \
  --source-label OpenAI \
  --source-url "https://x.com/OpenAI/status/..." \
  --canonical-url "https://openai.com/index/..." \
  --tier official \
  --evidence official_blog
```

### List ready-to-post candidates

```bash
python3 {baseDir}/scripts/state_db.py ready \
  --db /home/gc/.openclaw/workspace/data/model-news-hn-monitor/state.sqlite3 \
  --min-tier semi \
  --lookback-hours 96
```

### Mark an item as posted

```bash
python3 {baseDir}/scripts/state_db.py mark-posted \
  --db /home/gc/.openclaw/workspace/data/model-news-hn-monitor/state.sqlite3 \
  --item-key <item_key> \
  --submitted-url "https://openai.com/index/..." \
  --hn-url "https://news.ycombinator.com/item?id=..." \
  --title-used "OpenAI launches GPT-5.4 mini and nano"
```

### Check recent posting rate

```bash
python3 {baseDir}/scripts/state_db.py posts \
  --db /home/gc/.openclaw/workspace/data/model-news-hn-monitor/state.sqlite3 \
  --hours 24
```

## Dedupe against Hacker News before posting

Use the Algolia-backed checker:

```bash
python3 {baseDir}/scripts/hn_check.py \
  --url "https://openai.com/index/..." \
  --title "OpenAI launches GPT-5.4 mini and nano"
```

Skip posting when there is an equivalent URL or clearly equivalent title already on HN.

## Monitoring logic

### 1. Scan in layers

Use this order:
1. leak / early-signal accounts
2. official X accounts
3. official blogs / docs / changelogs
4. Hugging Face orgs / GitHub repos
5. OpenRouter and other distribution platforms

Use `web_search` / `web_fetch` for public discovery and reading.
Use `browser` when public reading is insufficient, dynamic pages matter, or logged-in browsing is required.
If a web task becomes complex, follow the same routing philosophy as the `web-access` skill instead of getting stuck on one method.

### 2. Ingest every useful signal

For every candidate model-release signal:
- normalize vendor + model name when possible
- ingest the signal into the DB immediately
- include evidence tags such as:
  - `official_blog`
  - `official_docs`
  - `hf`
  - `github`
  - `openrouter`
  - `api_model_id`
  - `model_card`

### 3. Auto-post threshold

Auto-post only when all are true:
- bootstrap mode is **off**
- local item is at least **semi** or **official**
- the item was seen within the configured recent lookback window
- there is a canonical URL worth submitting
- local DB does not show it as posted already
- HN dedupe check is clean
- last 24h posting count is below configured soft limit

Do **not** auto-post pure rumor items.

## Hacker News submission logic

Use the configured browser profile from:
- `/home/gc/.openclaw/workspace/data/model-news-hn-monitor/config.json`

Current default profile:
- `chrome-relay`

Submission target:
- `https://news.ycombinator.com/submitlink`

Submission method:
1. Open the submit page in the configured browser profile.
2. Verify the page shows the title/url form (that implies the login state is available).
3. Fill title + canonical URL.
4. Submit once.
5. Capture the resulting HN item URL if available.
6. Mark the item posted in the local DB.

If login state is missing or browser attachment fails:
- do not improvise a broken login flow
- leave the item queued
- try again on the next scheduled run or when the user restores browser access

## Title style

Write factual HN titles. Prefer:
- vendor + release verb + model name
- no hype words
- no clickbait framing

Examples:
- `Qwen releases Qwen 3.5 small model series`
- `OpenAI launches GPT-5.4 mini and nano`
- `DeepSeek releases DeepSeek-V3.2`

## Cron logic

Use an **isolated** cron agent turn for unattended monitoring.
Recommended default: every 15 minutes.

When creating the cron job, instruct the run to:
- use this skill
- initialize DB if missing
- scan the configured source layers
- ingest all signals
- check for ready-to-post items
- dedupe via HN checker
- post eligible items to HN
- exit quietly if nothing qualifies

Prefer quiet runs over noisy chat announcements unless the user explicitly wants notifications.
