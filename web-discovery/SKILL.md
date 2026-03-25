---
name: web-discovery
description: "Discover relevant public webpages and source candidates on the open web. Use when Codex needs to look up topics, news, documentation, blog posts, or source pages on the internet and does not already have the target page. Prefer Baidu AppBuilder search for China-related topics when `BAIDU_SEARCH_API_KEY` or `APPBUILDER_API_KEY` is configured; otherwise prefer Exa first, Tavily second, and only fall back to DuckDuckGo when paid providers are unavailable or skipped. Before searching, check the relevant provider keys before searching. In deeper research or credibility-sensitive tasks, use all available providers together to cross-check coverage before summarizing. If the target URL is already known and the task is primarily to read/extract page content, do not start with search; prefer `web-reader`, and upgrade to `web-access` once the task goes beyond pure reading."
---

# Web Discovery

Search the web with query-aware routing:

- **China-related topics**: Baidu -> Exa -> Tavily -> DuckDuckGo
- **Other topics**: Exa -> Tavily -> Baidu -> DuckDuckGo

`scripts/search.py` auto-detects Chinese-language and China-related queries, so the normal entrypoint stays the same.

## Quick Start

Before running any search command, check whether these keys are already configured:

- `BAIDU_SEARCH_API_KEY` or `APPBUILDER_API_KEY` for Baidu AppBuilder search
- `EXA_API_KEY`
- `TAVILY_API_KEY`

If any relevant key is missing, stop and ask the user directly. Mention only the missing keys:

```text
当前未配置以下 key（按实际缺失项列出）：
- BAIDU_SEARCH_API_KEY（中国相关内容优先；也可使用 APPBUILDER_API_KEY）：参考 https://ai.baidu.com/ai-doc/AppBuilder/pmaxd1hvy
- EXA_API_KEY：可以去 https://dashboard.exa.ai/api-keys 获取
- TAVILY_API_KEY：可以去 https://app.tavily.com/home 获取
要现在提供吗？如果你跳过，我会按当前可用 provider 继续回退；中国相关搜索会优先提示百度覆盖缺口。
```

Only after the user explicitly skips, or after configured providers still fail, may the agent rely on the remaining providers alone.

After the key situation is clear, run the initializer once before searching:

```bash
bash scripts/init_env.sh
```

Then run the search helper:

```bash
python3 scripts/search.py "your query" --max-results 5
```

For deeper research, use research mode so the helper collects from all available providers instead of stopping at the first success:

```bash
python3 scripts/search.py "your query" --mode research --max-results 5
```

## Workflow

1. First decide whether the task is discovery or reading:
   - If the URL/page is already known, or the job is mainly to read/extract one page, skip this skill and use `web-reader` or direct web access.
   - Use this skill only when you need to discover candidate pages.
2. Check whether the relevant provider keys exist before running any search command.
3. If a key is missing, stop and ask the user whether to provide it now.
4. If the user provides a key, ask the user to export it in the current shell or set it in persistent shell config before continuing.
5. Run `scripts/init_env.sh` to prepare the environment.
6. In normal search mode, let `scripts/search.py` route automatically:
   - China-related query -> Baidu first
   - Other query -> Exa first
7. In research mode, collect from all available providers, then compare overlaps and disagreements before summarizing.
8. If the user skips missing keys, continue with available providers, but explicitly note the coverage gap. For China-related queries, call out when Baidu coverage is unavailable.
9. After choosing result URLs, prefer the `web-reader` skill for page reading.
10. If `web-reader` is unavailable, read `references/reading.md` and follow its fallback ladder.

## Initializer Behavior

`scripts/init_env.sh` is only for environment preparation. It checks:

- whether `BAIDU_SEARCH_API_KEY` or `APPBUILDER_API_KEY` exists
- whether `EXA_API_KEY` exists
- whether `TAVILY_API_KEY` exists
- whether `duckduckgo-search` can be imported in `python3`
- whether a `web-reader` skill exists under `$CODEX_HOME/skills` or `~/.codex/skills`

If a provider key is missing, the script only prints a reminder. The agent, not the script, owns the user interaction.

## Search Helper

Use `scripts/search.py` for deterministic search behavior.

- Baidu path: call the Baidu AppBuilder web search API with `curl`.
- Exa path: call the Exa HTTP API with `curl`.
- Tavily path: call the Tavily HTTP API with `curl`.
- DuckDuckGo path: import `duckduckgo_search.DDGS`.
- Standard mode output: print JSON with the first successful provider.
- Research mode output: print JSON grouped by provider so another Codex instance can compare overlaps, titles, URLs, and snippets.

If a provider fails, surface the error once and fall back quickly. Do not add retry loops.

Examples:

```bash
python3 scripts/search.py "杭州 小升初 政策" --max-results 5
python3 scripts/search.py "next.js app router caching" --max-results 5
python3 scripts/search.py "中国 AI 搜索 API 对比" --mode research --max-results 5
python3 scripts/search.py "openclaw latest release" --max-results 8 --topic news
```

## Reading Pages

Do not embed a large page-reading workflow here. Read one of these instead:

- If `web-reader` exists: open that skill and follow it.
- Otherwise: open `references/reading.md`.

## Reliability Rules

- Do not retry providers in a loop. If a key is missing, ask the user once and stop. If the user skips or the provider fails, fall back quickly.
- For China-related topics, prefer Baidu whenever a Baidu key is configured.
- In research or credibility-sensitive tasks, prefer `--mode research` and compare all available providers.
- Do not assume `duckduckgo-search` is installed. Report the missing package clearly.
- Keep search results small. Start with `--max-results 5` unless the task needs broader coverage.
- Return URLs with the summary so the next step can fetch full page content only for the best candidates.
