---
name: web-research
description: "Search the web and fetch page content for research and content writing. Use when: (1) gathering reference material before writing content, (2) checking competitor pages, (3) researching keywords or topics, (4) finding Google PAA questions, (5) reading articles for inspiration. Provides Tavily search, DuckDuckGo search fallback, and jina.ai Reader for clean page extraction."
---

# Web Research Skill

Search the web and extract clean content from URLs for research purposes.

## Tools (use in order of preference)

### 1. Search — Tavily (primary, higher quality)

```python
from tavily import TavilyClient
client = TavilyClient(api_key="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")
result = client.search("your query", max_results=5)
for r in result['results']:
    print(r['title'], r['url'], r['content'][:200])
```

Monthly quota limited. Switch to ddgs if Tavily fails.

### 2. Search — DuckDuckGo (fallback, no quota)

Preferred:

```python
from ddgs import DDGS
results = DDGS().text("your query", max_results=5)
for r in results:
    print(r['title'], r['href'], r['body'][:200])
```

If `ddgs` is not installed or import fails, do **not** stop there. Use one of these fallbacks:

- Use the first-class `web_search` tool if available.
- Use Bing search result pages with `curl`/browser automation as a temporary SERP source.
- If DuckDuckGo HTML/lite triggers a bot challenge, switch sources instead of retry-looping.

### 3. Fetch full page — jina.ai Reader (primary)

```bash
curl -sL "https://r.jina.ai/https://example.com/page" -H "Accept: text/markdown" | head -300
```

Returns clean Markdown with title/meta. Works with JS-heavy sites, paywalls, Twitter/X.

### 4. Fetch full page — web_fetch (lightweight fallback)

Use OpenClaw's built-in `web_fetch` tool for simple pages that don't need JS rendering.

### 5. Browser SERP inspection — browser / agent-browser (when needed)

Use a browser when you need actual SERP layout details such as:
- Google PAA blocks
- related searches
- autocomplete / UI-only SERP hints
- dynamic result pages that simple fetch/search tools miss

WSL/Linux notes:
- If OpenClaw `browser` is unavailable, `agent-browser` is acceptable.
- In WSL, `agent-browser` may need Playwright Chromium installed first:

```bash
npx playwright install chromium
```

- If there is no desktop display, try a virtual display (`xvfb-run` / Xvfb) **only if already available**.
- Do not get stuck debugging browser infra for too long: if browser automation is blocked, continue with search + jina/web_fetch and note the limitation in the research file.

## Workflow

1. **Search** for the topic using Tavily or ddgs
2. **Pick** the 3-5 most relevant results
3. **Fetch** full content via jina.ai Reader
4. **Extract** key facts, data points, and quotes
5. **Use** as source material for content writing

## Reliability rules

- If one search source fails, switch quickly; do not burn time retrying the same broken path.
- Record environment limitations in the research file (e.g. `ddgs missing`, `DDG challenge`, `browser unavailable`).
- For copywriting/SEO work, research is only "done" once queries, sources, and extracted patterns are written to a file.

## Tips

- For Google PAA questions: search `"people also ask" + <topic>`
- For competitor analysis: search `site:<competitor.com> <topic>`
- Always save research to a local file before writing (e.g., `seo-plan/research/<topic>.md`)
- Quote sources when using specific data points
