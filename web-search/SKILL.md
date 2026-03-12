---
name: web-search
description: "Search the public web for up-to-date information and fetch readable page content. Use when Codex needs to look up topics, news, documentation, blog posts, or source pages on the internet. Prefer Exa first, then Tavily, and only fall back to DuckDuckGo when the paid providers are unavailable or skipped. Before searching, check both `EXA_API_KEY` and `TAVILY_API_KEY`; if either is missing, stop and ask the user whether to provide it now. In deeper research or credibility-sensitive tasks, use Exa, Tavily, and DuckDuckGo together to cross-check coverage before summarizing. For reading result pages, prefer a separate `web-reader` skill when present, otherwise use the fallback reading workflow in `references/reading.md`."
---

# Web Search

Search the web with an Exa-first workflow, a Tavily second pass, and a predictable DuckDuckGo fallback.

## Quick Start

Before running any search command, the agent must check whether `EXA_API_KEY` and `TAVILY_API_KEY` are already configured.

If either key is missing, the agent must stop and ask the user directly. Mention only the missing keys:

```text
当前未配置以下 key（按实际缺失项列出）：
- EXA_API_KEY：可以去 https://dashboard.exa.ai/api-keys 获取
- TAVILY_API_KEY：可以去 https://app.tavily.com/home 获取
要现在提供吗？如果你跳过，我会按 Exa -> Tavily -> DuckDuckGo 的顺序继续回退。
```

Only after the user explicitly skips, or after Exa and Tavily still fail with provided keys, may the agent rely on DuckDuckGo alone.

After the key situation is clear, run the initializer once before searching:

```bash
bash scripts/init_env.sh
```

Then run the search helper:

```bash
python3 scripts/search.py "your query" --max-results 5
```

For deeper research, use the research mode so the helper collects from all providers instead of stopping at the first success:

```bash
python3 scripts/search.py "your query" --mode research --max-results 5
```

## Workflow

1. Check whether `EXA_API_KEY` and `TAVILY_API_KEY` exist before running any search command.
2. If either key is missing, stop and ask the user whether to provide it now.
3. If the user provides a key, ask the user to export it in the current shell or set it in persistent shell config before continuing.
4. Run `scripts/init_env.sh` to prepare the fallback environment.
5. In normal search mode, use Exa first, Tavily second, and DuckDuckGo last.
6. In research mode, collect from Exa, Tavily, and DuckDuckGo together, then compare overlaps and disagreements before summarizing.
7. If the user skips missing keys, continue with the providers that are available, but explicitly note the coverage gap in the answer.
8. After choosing result URLs, prefer the `web-reader` skill for page reading.
9. If `web-reader` is unavailable, read `references/reading.md` and follow its fallback ladder.

## Initializer Behavior

`scripts/init_env.sh` is only for environment preparation. It checks:

- whether `EXA_API_KEY` exists
- whether `TAVILY_API_KEY` exists
- whether `duckduckgo-search` can be imported in `python3`
- whether a `web-reader` skill exists under `$CODEX_HOME/skills` or `~/.codex/skills`

If either paid-provider key is missing, the script only prints a reminder:

```text
当前未配置 EXA_API_KEY
可以去 https://dashboard.exa.ai/api-keys 获取
请先由 agent 询问用户是否现在提供 key。

当前未配置 TAVILY_API_KEY
可以去 https://app.tavily.com/home 获取
请先由 agent 询问用户是否现在提供 key。

如果用户跳过，搜索将按 Exa -> Tavily -> DuckDuckGo 顺序回退。
```

The agent, not the script, owns the user interaction.

## Search Helper

Use `scripts/search.py` for deterministic search behavior.

- Exa path: call the Exa HTTP API with `curl`.
- Tavily path: call the Tavily HTTP API with `curl`, so no Tavily SDK is required and local proxy/certificate handling is usually more reliable than Python `urllib`.
- DuckDuckGo path: import `duckduckgo_search.DDGS`.
- Standard mode output: print JSON with the first successful provider.
- Research mode output: print JSON grouped by provider so another Codex instance can compare overlaps, titles, URLs, and snippets.

If Exa or Tavily fails, surface the curl error once and fall back quickly. Do not add retry loops.

Examples:

```bash
python3 scripts/search.py "next.js app router caching" --max-results 5
python3 scripts/search.py "best ai coding agent benchmark" --mode research --max-results 5
python3 scripts/search.py "openclaw latest release" --max-results 8 --topic news
```

## Reading Pages

Do not embed a large page-reading workflow here. Read one of these instead:

- If `web-reader` exists: open that skill and follow it.
- Otherwise: open `references/reading.md`.

## Reliability Rules

- Do not retry Exa or Tavily in a loop. If a key is missing, ask the user once and stop. If the user skips or the provider fails, fall back quickly.
- In research or credibility-sensitive tasks, prefer `--mode research` and compare Exa, Tavily, and DuckDuckGo outputs whenever those three providers are available.
- Do not assume `duckduckgo-search` is installed. Report the missing package clearly.
- Keep search results small. Start with `--max-results 5` unless the task needs broader coverage.
- Return URLs with the summary so the next step can fetch full page content only for the best candidates.
