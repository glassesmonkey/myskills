---
name: web-reader
description: "Fetch readable content from public webpages. Use when Codex needs to read an article, blog post, documentation page, or other public URL and return clean text or Markdown for analysis. Prefer this skill when the job is page reading rather than web search. It uses Jina Reader first via `https://r.jina.ai/YOUR_URL`, then falls back to Scrapling + html2text when Jina fails, returns an error page, or produces empty content."
---

# Web Reader

Read a public webpage into model-friendly Markdown with the lowest-friction path first.

The default flow is:
1. Try Jina Reader with `https://r.jina.ai/YOUR_URL`
2. If Jina fails or returns unusable output, fetch the page with Scrapling
3. Convert the main content HTML to Markdown with html2text

## Quick Start

Install fallback dependencies once:

```bash
bash scripts/init_env.sh
```

Read a page with automatic fallback:

```bash
python3 scripts/read_url.py "https://example.com/article"
```

Force one route when debugging:

```bash
python3 scripts/read_url.py "https://example.com/article" --mode jina
python3 scripts/read_url.py "https://example.com/article" --mode scrapling
```

## Workflow

### 1. Use Jina Reader first

Construct the request as:

```text
https://r.jina.ai/YOUR_URL
```

Example:

```text
https://r.jina.ai/https://example.com/article
```

Use Jina first because it is usually the cleanest and cheapest way to turn a public article page into Markdown.

Treat Jina as failed when:
- the HTTP request errors or times out
- the response is empty or too short to be useful
- the response looks like an error page or rate-limit page
- the user explicitly needs the fallback route

### 2. Fall back to Scrapling + html2text

Use the bundled script. It:
- downloads raw page HTML
- parses the HTML with Scrapling
- tries article-like selectors first
- fixes common lazy-image attributes
- converts the selected HTML block to Markdown with html2text

This fallback is better when the page is public but Jina returns nothing useful.

### 3. Return only readable content

The goal is not full-page HTML. Return the readable article or main content block in Markdown. Avoid nav, footer, cookie banners, and unrelated UI text when possible.

## Reliability Rules

- Do not loop on Jina retries. One failed Jina attempt is enough to switch.
- If Scrapling dependencies are missing, run `bash scripts/init_env.sh`.
- If both routes fail, report which route failed and why.
- Use `--mode scrapling` to verify the fallback path directly.
- Prefer this skill for public page reading only. If the page requires login, clicking, or scrolling to reveal content, use a browser automation workflow instead of forcing this skill.

## Scripts

- `scripts/read_url.py`: automatic route selection and webpage-to-Markdown extraction
- `scripts/init_env.sh`: local install for fallback Python dependencies
