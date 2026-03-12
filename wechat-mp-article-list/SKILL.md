---
name: wechat-mp-article-list
description: Open the WeChat Official Account backend in Chrome DevTools MCP, wait for the user to log in, enter the article editor hyperlink dialog, search a target public account, and extract that account's article list from the official backend UI or its network responses. Use when Codex needs to read historical articles for a target WeChat public account through mp.weixin.qq.com instead of third-party crawlers.
---

# WeChat MP Article List

Use the official WeChat Official Account backend and Chrome DevTools MCP to read article lists for a target public account after the user logs in.

## Workflow

1. Open `https://mp.weixin.qq.com/` and wait for the user to complete login.
2. Enter the article editor.
3. Open the hyperlink toolbar item in the editor.
4. In the hyperlink dialog, keep the mode that selects an account article instead of typing a raw URL.
5. Use the option that switches to another account, search the target account name or alias, and select the correct account.
6. Read the article list.
7. Prefer structured network responses. Fall back to visible DOM rows only if needed.
8. When fetching many pages, use the rate-limit strategy documented in [references/backend-workflow.md](references/backend-workflow.md) instead of issuing rapid-fire page requests.

## Operating Rules

- Keep login manual. Never ask for credentials or try to bypass QR approval.
- Re-snapshot after each click in the editor flow because the dialog content updates in place.
- Prefer network extraction over DOM extraction.
- Treat endpoint names as current working knowledge, not permanent contracts.
- If the first search result is ambiguous, verify the account nickname and alias before selecting it.
- Never fetch pages in parallel.
- For bulk extraction, prefer larger page sizes that reduce request count, then add a short delay between requests.
- If the backend returns `base_resp.ret = 200013` or `err_msg = "freq control"`, pause and retry the same page instead of continuing to the next page.
- Deduplicate links before returning or saving output because some pages can contain repeated items or multi-item publish records.

## Current Verified Path

Read [references/backend-workflow.md](references/backend-workflow.md) before using the skill. It contains the currently verified UI path, request URLs, and the response fields observed in a live session.

## Output Contract

Return a compact JSON array or markdown table with:

- `account_name`
- `account_alias`
- `fakeid`
- `article_title`
- `publish_time`
- `link`
- `cover`
- `source`

Use `source: "network"` when the data comes from `search_biz` plus `list_ex`. Use `source: "dom"` only when the network body is unavailable.
