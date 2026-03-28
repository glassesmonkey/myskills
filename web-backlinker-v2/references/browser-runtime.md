# Browser Runtime

Use one brain and two execution layers:

1. `browser-use` CLI for navigation, probing, light interaction, and readback.
2. Playwright for deterministic field fills, assertions, screenshots, and submit/review steps.

Both layers must attach to the same Chrome DevTools Protocol target.

## Canonical Rule

- Give `browser-use` the shared **HTTP/WebSocket CDP URL**.
- Give Playwright the **WebSocket debugger URL** from `.../json/version`.
- Never hardcode a WSL-only host into the skill. Read the endpoint from args or environment.

Environment variables checked in order:

1. `BACKLINK_BROWSER_CDP_URL`
2. `BROWSER_USE_CDP_URL`
3. `CHROME_CDP_URL`

For the `browser-use` binary itself, use either:

- `BACKLINK_BROWSER_USE_BIN`
- `BROWSER_USE_BIN`

If neither is set, the skill falls back to PATH, then common home-directory install locations.

Examples:

```bash
export BACKLINK_BROWSER_CDP_URL=http://127.0.0.1:9222
export BACKLINK_BROWSER_CDP_URL=http://172.31.240.1:9222
export BACKLINK_BROWSER_CDP_URL=ws://host:9222/devtools/browser/<id>
```

If the configured value is HTTP, resolve `playwright_ws_url` from `http://host:port/json/version`.
If the configured value is already WebSocket, reuse it directly for Playwright.

## Provider Policy

Prefer providers in this order:

1. `browser-use-cli` with shared CDP
2. `bb-browser`
3. `dry-run`

Use `scripts/preflight.py` to compute the default provider. It now records `browser_runtime` into the manifest so later worker steps can reuse the same endpoint.

## Handoff Rules

Switch by **phase**, not by individual click:

- `browser-use` phase: find entry, detect route, observe branching, collect cheap evidence.
- Playwright phase: execute a stable form segment, assert values, click deterministic controls, capture final evidence.

Only hand off on a stable checkpoint:

- expected URL prefix reached
- step marker visible
- main form root present
- loading state cleared

## Ownership Rules

- One executor writes at a time.
- `browser-use` and Playwright may share the same browser, but they must not both click/type concurrently.
- Treat Playwright as the submit/assertion layer by default.

## Genericity Rules

Keep the skill portable across WSL, Linux, macOS, and Windows-hosted Chrome:

- do not assume `127.0.0.1` unless the operator configured it
- do not assume WSL interop IPs are stable
- read CDP endpoint from env/args/manifest runtime state
- prefer command availability checks that work outside Unix-only `which`

## Scripts

- `scripts/browser_runtime.py`: resolve `cdp_url` and `playwright_ws_url`
- `scripts/playwright_cdp.py`: run deterministic Playwright actions against the same shared browser
- `scripts/preflight.py`: verify `browser-use`, CDP reachability, and provider preference

## Current Scope

The skill now wires the shared-CDP runtime into preflight and the execution core. Adapters can consume:

- `context.cdpUrl`
- `context.playwrightWsUrl`
- `context.browserRuntime`

Use those fields when adding site-specific Playwright-backed adapters later.
