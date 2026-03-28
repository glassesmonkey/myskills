---
name: web-backlinker-v2
description: Automate repeatable backlink and directory-submission campaigns for a promoted website. Use when Codex needs to scout submission targets, build a reusable promoted-site profile from a user-supplied URL, generate UTM-tagged submission links, register or reuse site accounts through email signup or Google OAuth, read verification emails with the Google Workspace `gog` CLI, remember successful site-specific submission playbooks for future reuse, and drain a task list autonomously without pausing on each row.
---

# Web Backlinker V2

Turn backlink work into a resumable system instead of a one-off browser sprint. The core idea is:

1. Learn the promoted site once.
2. Learn each target site once.
3. Reuse both memories on later runs.

## Read These References When Needed

- `references/architecture.md`
  Use for the overall design, the borrowed ideas from the two reference projects, and the deliberate improvements in this skill.
- `references/init-intake.md`
  Read before the first real worker run. Use it to collect required business facts and policy boundaries, then keep the run in `WAITING_CONFIG` until the intake is complete.
- `references/runtime.md`
  Use before bootstrapping or draining a task list.
- `references/browser-runtime.md`
  Use when configuring shared Chrome CDP execution, `browser-use` CLI, or Playwright handoff.
- `references/site-memory.md`
  Use when deciding whether to probe again, reuse an old route, or promote a successful path into a stable playbook.
- `references/auth-and-verification.md`
  Use before any signup, OAuth, magic-link, or email-verification flow.
- `references/captcha-policy.md`
  Read before interacting with any CAPTCHA or anti-bot surface.
- `references/profile-probing.md`
  Use when building the promoted-site material pack or when a form asks for facts that are still missing.
- `references/target-scouting.md`
  Use when a target site is new and the skill needs to classify submit links, forms, login mode, and anti-bot level.
- `references/worker-brief.md`
  Use before opening a browser worker so the worker only reads the smallest useful context.

## Default Workflow

1. Bootstrap runtime storage.

```bash
python3 scripts/bootstrap_runtime.py \
  --campaign "march-launch" \
  --promoted-url "https://example.com"
```

2. Probe the promoted site before touching targets.

```bash
python3 scripts/probe_promoted_site.py \
  --url "https://example.com" \
  --out data/backlink-helper/profiles/example.com.json
```

3. Initialize intake and block the run until required fields are present.

```bash
python3 scripts/init_intake.py \
  --manifest data/backlink-helper/runs/<run-id>.json
```

If `required_missing` is non-empty:

- ask the user for those fields immediately in natural Chinese
- do not expose raw schema keys to the user unless the user explicitly wants the low-level format
- use semantic understanding to map the user's natural-language reply back into the structured fields
- do not scout target sites yet
- do not open submission pages yet
- do not attempt signup, login, or submission
- do not switch to other browser tools to continue anyway

4. Run environment preflight and inspect the default provider.

```bash
python3 scripts/preflight.py \
  --manifest data/backlink-helper/runs/<run-id>.json \
  --bb-mode auto \
  --cdp-url "$BACKLINK_BROWSER_CDP_URL"
```

If `--cdp-url` is omitted, preflight falls back to `BACKLINK_BROWSER_CDP_URL`, `BROWSER_USE_CDP_URL`, then `CHROME_CDP_URL`.

`bb-mode` meanings:

- `auto`: always use standalone extension mode in Codex; never auto-route into OpenClaw
- `openclaw`: only for runs that are actually executing inside OpenClaw; do not use this from Codex
- `standalone_extension`: use direct CLI mode against the real Chrome bridge
- `mcp`: record MCP intent, but current worker does not execute through MCP yet
- `disabled`: skip bb-browser entirely and default to `dry-run`

## Browser Routing Rules

- Prefer shared-CDP `browser-use-cli` when a reusable Chrome endpoint is configured.
- Use Playwright as the deterministic assertion / final-submit layer on top of that same shared CDP browser when an adapter needs stronger guarantees.
- Fall back to `bb-browser` only when shared CDP is unavailable or the operator explicitly prefers it.
- In Codex, never auto-invoke OpenClaw just because `bb-browser` supports `--openclaw`.
- In Codex, if `bb-mode=openclaw` is requested anyway, preflight must stop and tell the operator to use `standalone_extension` or move the whole run into OpenClaw.
- Do not switch to unrelated browser stacks mid-submission just because one provider is temporarily awkward. Resolve provider choice in preflight, then keep one shared browser context per task.
- If both shared-CDP `browser-use-cli` and `bb-browser` preflight fail, stop and report the failure clearly. Do not silently continue the same submission flow with a different browser stack.

5. Import the target list and apply cross-run dedupe.

```bash
python3 scripts/task_store.py init \
  --run-id "<run-id>" \
  --targets-file targets.txt \
  --promoted-url "https://example.com"
```

6. Drain the queue in small, resumable worker cycles.
   Claim one row, inspect the current playbook and account memory, submit or park that row, persist the result, then claim the next row.

7. Scout only when memory is missing.

```bash
python3 scripts/scout_target.py \
  --url "https://target-site.com" \
  --deep \
  --out /tmp/target-scout.json
```

8. Convert the first scout into reusable memory.

```bash
python3 scripts/scaffold_playbook.py \
  --scout-file /tmp/target-scout.json
```

9. Build a compact worker brief before execution.

```bash
python3 scripts/prepare_worker_brief.py \
  --store data/backlink-helper/tasks/<run-id>.json \
  --task-id "<task-id>" \
  --profile data/backlink-helper/profiles/example.com.json
```

10. Drain one runnable task through the actual worker entrypoint.

```bash
python3 scripts/run_next.py \
  --manifest data/backlink-helper/runs/<run-id>.json \
  --provider auto
```

For unattended queue draining, prefer the small-batch wrapper so one cron tick can process a few rows serially without overlapping another worker:

```bash
python3 scripts/run_batch.py \
  --manifest data/backlink-helper/runs/<run-id>.json \
  --provider auto \
  --max-tasks 3 \
  --task-timeout 480 \
  --max-seconds 1320
```

11. Record reusable memory immediately after each meaningful result.
   On success, update the site playbook and submission ledger.
   On account creation, update the account registry.
   On email verification, keep the mailbox account and verification style in memory.

## Operating Rules

- Always probe the promoted site first, even if the user only gave a homepage URL.
- Always run `scripts/init_intake.py` before the first real submission worker.
- Always stop and ask for missing intake fields before scouting targets if intake is incomplete.
- Always inspect the `preflight.default_provider` before expecting real-submit execution.
- Always build the submitted URL through `scripts/build_utm_url.py`.
- Always check the existing site playbook before probing a known target again.
- Always check the account registry before opening a new signup flow.
- Always keep probing promising target-site paths without pausing for operator confirmation, until one of three things happens: (1) a real submit form is found, (2) a hard boundary is confirmed, or (3) the route is proven dead (404/paywall/no live submit path).
- Always park one blocked row and continue with the rest of the list.
- Never submit the same promoted site to the same target twice.
- Never bypass Cloudflare, reCAPTCHA, hCaptcha, or managed anti-bot walls.
- Never auto-accept reciprocal backlink or badge-exchange requirements; park the row as `WAITING_HUMAN` and tag it with blocker type `reciprocal_backlink_required`.
- Never invent product claims, prices, customers, or company facts.
- Never start submit/signup/verify steps while the run is still `WAITING_CONFIG`.
- Never route a real submission flow into Chrome DevTools or another browser stack just because `bb-browser` is not ready.

## Route Preference

Prefer routes in this order unless the target site clearly forces something else:

1. Exact site playbook replay
2. Reuse existing site account
3. No-auth direct submit
4. Email signup
5. Google OAuth
6. Park the row for later review

Email signup is preferred over OAuth when both are equally practical. OAuth is allowed when the site strongly prefers it and the scopes look normal. If the shared browser session already has a live Google or Facebook login, treat that as a reusable path and attempt the OAuth route instead of parking it by default.

## Continuous Execution Model

Treat one target URL as one recoverable task. Keep moving without asking the user after every row.

- `READY`: can be worked now
- `RUNNING`: currently claimed by a worker
- `WAITING_EMAIL`: waiting for verification mail or magic link
- `WAITING_HUMAN`: worth doing, but a human decision or credential is required
- `RETRYABLE`: retry later
- `DONE`: terminal success
- `SKIPPED`: terminal non-success

When a row hits a blocker, update the task state, add a short note, and continue with another row. Do not keep burning tokens on the same wall.

## Promoted-Site Material Pack

The promoted-site profile is not optional. Build it early and refresh it when forms reveal missing fields.

The material pack should eventually contain:

- canonical URL
- product name
- short and medium descriptions
- category and tags
- core features
- target audience and use cases
- pricing page
- privacy or trust page
- contact email choices
- founder or company facts only when evidence-backed

Use `scripts/probe_promoted_site.py` first. Re-run it with additional `--need` values when later forms expose missing facts.

## Mail And Verification

Use `scripts/gmail_watch.py` as the only default mail-reading path for automated verification flows. It wraps the Google Workspace `gog` CLI and is suitable for:

- verification links
- magic links
- one-time codes
- welcome mails that confirm account creation

If `gog` is missing or not configured, mark the row or run as waiting for config instead of pretending the mailbox step is complete.

## CAPTCHA Boundary

Use the policy in `references/captcha-policy.md`.

Short version:

- simple text, math, or obvious single-image prompts: one careful attempt is allowed
- Cloudflare, Turnstile, reCAPTCHA, hCaptcha, or managed challenge loops: stop and skip the row

## Bundled Scripts

- `scripts/bootstrap_runtime.py`: create the runtime layout and run manifest
- `scripts/build_utm_url.py`: create tracked submission URLs
- `scripts/probe_promoted_site.py`: build or refresh the promoted-site material pack
- `scripts/init_intake.py`: merge inferred profile facts with operator-provided required fields and enforce `WAITING_CONFIG`
- `scripts/browser_runtime.py`: resolve shared-CDP browser endpoints for `browser-use` CLI and Playwright
- `scripts/playwright_cdp.py`: run deterministic Playwright actions against the same shared browser
- `scripts/preflight.py`: verify local execution prerequisites such as shared CDP reachability, `browser-use`, `bb-browser`, `gog`, `node`, and `pnpm`
- `scripts/scout_target.py`: scout a target site and classify forms, auth, anti-bot, and likely submit entrypoints
- `scripts/scaffold_playbook.py`: turn a fresh scout result into a reusable site playbook stub
- `scripts/prepare_worker_brief.py`: compress task, profile, playbook, and account memory into one worker-ready brief
- `scripts/task_store.py`: initialize, claim, checkpoint, finish, and summarize task state
- `scripts/playbook_memory.py`: persist and reuse per-site submission playbooks
- `scripts/account_registry.py`: persist reusable target-site accounts
- `scripts/select_execution_plan.py`: choose the next route from task, playbook, and account memory
- `scripts/gmail_watch.py`: find verification emails, links, and OTP codes through `gog`
- `scripts/run_next.py`: claim one runnable task, scout it, select a route, and execute or park it
- `scripts/run_batch.py`: hold a run-level single-flight lock and execute a small serial batch of `run_next` calls for unattended cron workers

## Execution Core

Install the JavaScript execution layer once before using browser-backed submission:

```bash
pnpm install
```

The Node execution core lives under `packages/execution-core/` and is responsible for:

- provider abstraction (`browser-use-cli`, `bb-browser`, `dry-run`, `manual`)
- adapter selection for known sites
- generic form-submit fallback
- cheap scout output for browser-oriented paths
- passing shared-CDP runtime (`cdpUrl`, `playwrightWsUrl`) into adapters
