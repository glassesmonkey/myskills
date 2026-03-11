---
name: web-search
description: "Search the public web for up-to-date information and fetch readable page content. Use when Codex needs to look up topics, news, documentation, blog posts, or source pages on the internet. Prefer Tavily for search quality, but before running search commands the agent must check whether `TAVILY_API_KEY` exists; if it is missing, stop and ask the user whether to provide it now, and only use DuckDuckGo via `duckduckgo-search` when the user explicitly skips or Tavily still fails. For reading result pages, prefer a separate `web-reader` skill when present, otherwise use the fallback reading workflow in `references/reading.md`."
---

# Web Search

Search the web with a Tavily-first workflow and a predictable DuckDuckGo fallback.

## Quick Start

Before running any search command, the agent must check whether `TAVILY_API_KEY` is already configured.

If it is missing, the agent must stop and ask the user directly:

```text
当前未配置 TAVILY_API_KEY
可以去 https://app.tavily.com/home 获取
要现在提供吗？如果你跳过，我再回退到 DuckDuckGo。
```

Only after the user explicitly skips, or after Tavily still fails with a provided key, may the agent use DuckDuckGo.

After the key situation is clear, run the initializer once before searching:

```bash
bash scripts/init_env.sh
```

Then run the search helper:

```bash
python3 scripts/search.py "your query" --max-results 5
```

## Workflow

1. Check whether `TAVILY_API_KEY` exists before running any search command.
2. If the key is missing, stop and ask the user whether to provide it now.
3. If the user provides a key, ask the user to export it in the current shell or set it in persistent shell config before continuing.
4. Run `scripts/init_env.sh` to prepare the fallback environment.
5. If `TAVILY_API_KEY` exists, use Tavily first.
6. If the user skips input or Tavily fails, fall back to DuckDuckGo through `duckduckgo-search`.
7. After choosing result URLs, prefer the `web-reader` skill for page reading.
8. If `web-reader` is unavailable, read `references/reading.md` and follow its fallback ladder.

## Initializer Behavior

`scripts/init_env.sh` is only for environment preparation. It checks:

- whether `duckduckgo-search` can be imported in `python3`
- whether a `web-reader` skill exists under `$CODEX_HOME/skills` or `~/.codex/skills`

If `TAVILY_API_KEY` is missing, the script only prints a reminder:

```text
当前未配置 TAVILY_API_KEY
可以去 https://app.tavily.com/home 获取
请先由 agent 询问用户是否现在提供 key。
如果用户跳过，再回退到 DuckDuckGo。
```

The agent, not the script, owns the user interaction.

## Search Helper

Use `scripts/search.py` for deterministic search behavior.

- Tavily path: call the Tavily HTTP API directly, so no extra Tavily SDK is required.
- DuckDuckGo path: import `duckduckgo_search.DDGS`.
- Output: print JSON so another Codex instance can inspect titles, URLs, snippets, and which provider was used.

Examples:

```bash
python3 scripts/search.py "next.js app router caching" --max-results 5
python3 scripts/search.py "openclaw latest release" --max-results 8 --topic news
```

## Reading Pages

Do not embed a large page-reading workflow here. Read one of these instead:

- If `web-reader` exists: open that skill and follow it.
- Otherwise: open `references/reading.md`.

## Reliability Rules

- Do not retry Tavily in a loop. If the key is missing, ask the user once and stop. If the user skips or Tavily fails, fall back quickly.
- Do not assume `duckduckgo-search` is installed. Report the missing package clearly.
- Keep search results small. Start with `--max-results 5` unless the task needs broader coverage.
- Return URLs with the summary so the next step can fetch full page content only for the best candidates.
