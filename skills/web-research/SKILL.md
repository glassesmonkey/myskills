---
name: web-research
description: "Search the web and fetch readable page content for research and content writing. Use when: (1) gathering reference material before writing content, (2) checking competitor pages, (3) researching keywords or topics, (4) finding Google PAA questions, (5) reading articles or extracting webpage正文. Supports Tavily / DuckDuckGo search plus multi-tier page extraction via jina.ai Reader, Scrapling+html2text, web_fetch, and browser/playwright-cli escalation for login-gated or dynamic pages."
---

# Web Research Skill

Search the web and extract readable content from URLs for research purposes.

## Search tools

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

## Readable page extraction ladder

The goal is **正文提纯** for model consumption, not dumping the whole page into context.

### 3. Jina Reader — primary for public article pages

```bash
curl -sL "https://r.jina.ai/http://example.com/page" -H "Accept: text/markdown"
```

Use first for:
- public blog posts
- Substack / Medium style pages
- general research reading

Benefits:
- fast
- clean Markdown
- usually lowest token cost for article reading

Limitations:
- quota limited
- can fail on WeChat / some domestic sites / some protected pages

### 4. Scrapling + html2text — fallback for anti-bot/public dynamic pages

Use bundled script when:
- Jina fails or is empty
- target is WeChat article / Zhihu / Juejin / CSDN
- page is public but raw fetch is noisy

Script:
```bash
python3 scripts/fetch_readable.py <url> 30000
```

What it does:
- fetches page HTML with Scrapling
- tries article-like selectors first
- repairs lazy-loaded image attributes on common sites
- converts selected HTML to Markdown with html2text

### 5. web_fetch — static fallback

Use the built-in `web_fetch` tool for:
- GitHub README
- ordinary static documentation pages
- simple pages that do not need JS rendering

Caution:
- often includes nav/sidebar/footer noise

### 6. Browser / playwright-cli escalation — login state or interaction required

Escalate when:
- page requires login
- content appears only after hydration
- you need to click `Read more` / `展开全文` / `Load more`
- infinite scroll or consent wall blocks the content
- persistent cookies / localStorage are required

Read `references/playwright-cli-reading.md` before using this route.

Important:
- browser automation is for **revealing** the real content
- then extract only the content container HTML and convert it to Markdown
- do **not** feed full accessibility trees or full-page snapshots into the model unless necessary

## Fast domain routing

Use Scrapling first for:
- `mp.weixin.qq.com`
- `zhuanlan.zhihu.com`
- `juejin.cn`
- `csdn.net`

Use Jina or web_fetch first for:
- `github.com`
- public docs/blog pages

Use browser / playwright-cli first for:
- login-gated sites
- dashboards / apps
- pages that need interaction before content appears

## Workflow

1. **Search** for the topic using Tavily or ddgs
2. **Pick** the 3-5 most relevant results
3. **Fetch readable content** using the extraction ladder above
4. **Extract** key facts, data points, and quotes
5. **Write findings to a local research file** before drafting content

## Reliability rules

- If one search source fails, switch quickly; do not burn time retrying the same broken path.
- If one extraction route fails, escalate to the next route instead of looping.
- Record environment limitations in the research file (e.g. `ddgs missing`, `browser unavailable`, `playwright-cli not installed`).
- For copywriting/SEO work, research is only "done" once queries, sources, and extracted patterns are written to a file.
- If the same URL fails twice, stop retrying and mark it as not extractable with the current environment.

## Local environment notes

- On this host, `python3 -m venv` may fail if `python3-venv` is not installed.
- Prefer isolated local installs (`pip --target <dir>`) over mutating system Python.
- `playwright-cli` is optional and should not be assumed present.

## Tips

- For Google PAA questions: search `"people also ask" + <topic>`
- For competitor analysis: search `site:<competitor.com> <topic>`
- Always save research to a local file before writing (e.g., `seo-plan/research/<topic>.md`)
- Quote sources when using specific data points
