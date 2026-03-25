# Tool routing — upstream `web-access` → OpenClaw-native

## Core mapping

- Upstream **WebSearch** → OpenClaw `web_search`
- Upstream **WebFetch** → OpenClaw `web_fetch`
- Upstream **curl + Jina + raw HTML probing** → usually `web_fetch`; only use alternate fetch routes when the public-page goal is not satisfied
- Upstream **CDP proxy (`localhost:3456`)** → OpenClaw `browser`
- Upstream **sub-agent fanout** → OpenClaw `sessions_spawn`
- Upstream **site-pattern files** → `references/site-patterns/*.md`

## OpenClaw routing rules

### 1. Source discovery
Default to the workspace `web-discovery` skill when you need to find candidate sources, official pages, or competing references. Use the built-in `web_search` tool only as a fallback or when the skill is unavailable.

### 2. Public-page reading
Default to **`web-reader`** when:
- the URL is already known
- the page is public
- the goal is to read/extract正文 rather than interact
- the page is article/docs/blog/help-center/news-like

In OpenClaw terms, that means preferring either:
- `web_fetch`, or
- `skills/web-access/scripts/read_url.py` for Jina-first readable extraction with Scrapling fallback

If the task grows beyond “read the page” into search / login / click / scroll / dynamic interaction, upgrade to the broader `web-access` workflow.

### 3. Real browser work
Use `browser` when:
- the page is dynamic or JS-heavy
- the task needs clicking, typing, uploads, or scrolling
- existing login state matters
- anti-bot/static extraction is likely to fail

Browser profile choice:
- anonymous/public → default isolated browser
- existing local login state matters → `profile="user"`
- user explicitly says relay / attach tab / Browser Relay → `profile="chrome-relay"`

### 4. Parallel fanout
Use `sessions_spawn` when the targets are independent enough that a worker can finish with its own local context and return only a summary.

Good cases:
- compare 5 competitors
- inspect 20 pages
- research multiple platforms in parallel

Bad cases:
- later tasks depend on earlier task outputs
- the total job is so small that worker startup dominates

## What not to port literally

Do not port these upstream assumptions literally into OpenClaw:
- `~/.claude/skills/...`
- `bash ~/.claude/skills/web-access/scripts/check-deps.sh`
- `node .../cdp-proxy.mjs`
- `curl http://localhost:3456/...`

Those are implementation details for Claude Code, not the essence of the design.

## OpenClaw-native acceptance criteria

A correct OpenClaw adaptation should:
1. preserve the four-step decision loop
2. route search / read / browser tasks through first-class tools
3. use user-browser profiles only when needed
4. avoid interfering with the user's existing tabs unless required
5. support per-domain experience files that can be updated over time
