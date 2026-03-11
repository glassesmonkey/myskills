# Reading Fallback

Use this file only when the `web-reader` skill is unavailable.

## Decision Order

1. Try the built-in web fetching capability first for ordinary public pages.
2. If the page is article-like and the raw HTML is noisy, try:

```bash
curl -sL "https://r.jina.ai/http://example.com/page"
```

3. If the page needs interaction, browser state, or client-side rendering, escalate to browser automation.

## Rules

- Read only the pages you actually need after ranking search results.
- Prefer readable extracts over full-page dumps.
- Keep the final summary tied to the source URL.
- If one read path fails twice, switch methods instead of looping.
