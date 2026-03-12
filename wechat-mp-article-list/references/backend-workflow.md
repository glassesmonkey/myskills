# Backend Workflow

## Verified On

Verified in a live session on March 12, 2026 against `https://mp.weixin.qq.com/` using Chrome DevTools MCP.

## Verified UI Path

1. Open `https://mp.weixin.qq.com/`.
2. Wait for the user to log in.
3. From the home page, enter the new creation flow for an article.
4. In the editor page, click the hyperlink toolbar item.
5. In the hyperlink dialog:
   - keep the content mode on selecting an account article
   - click the option that switches to another account
   - search the target account name or alias
   - click the matching account row
6. Read the article list shown in the content selection area.

## Verified Current Editor Route

The editor opened at a route like:

`https://mp.weixin.qq.com/cgi-bin/appmsg?t=media/appmsg_edit_v2&action=edit&isNew=1&type=77&createType=0&token=...`

Do not hard-code the full URL. Only rely on the fact that the editor page exposes a hyperlink toolbar item and a hyperlink editing dialog.

## Verified Search Response

Current account search request:

`GET /cgi-bin/searchbiz?action=search_biz&begin=0&count=5&query=<urlencoded-query>&...`

Verified response fields:

- `list[].fakeid`
- `list[].nickname`
- `list[].alias`
- `list[].round_head_img`
- `list[].signature`
- `list[].verify_status`

Example from the live run for query `gefei` / `Ge Fei`:

- nickname: `Ge Fei` in Chinese
- alias: `gefei7`
- fakeid: `MjM5OTIzMzYyMA==`

## Verified Article List Response

Current article list request after selecting an account:

`GET /cgi-bin/appmsgpublish?sub=list&search_field=null&begin=0&count=5&query=&fakeid=<fakeid>&type=101_1&free_publish_type=1&sub_action=list_ex&...`

The live response returned:

- `publish_page`
  - this is a JSON string, not a nested object
- inside parsed `publish_page`
  - `total_count`
  - `publish_count`
  - `masssend_count`
  - `publish_list[]`
- inside each `publish_list[]`
  - `publish_type`
  - `publish_info`
  - `publish_info` is another JSON string
- inside parsed `publish_info`
  - `sent_info.time`
  - `appmsgex[]`
- inside each `appmsgex[]`
  - `title`
  - `cover`
  - `link`
  - `digest`
  - `update_time`
  - `create_time`
  - `author_name`
  - `appmsgid`
  - `itemidx`
  - optional album and cover variants

## Parsing Rule

Use this order:

1. Parse the outer response JSON.
2. Parse `publish_page` as JSON.
3. For each `publish_list[]`, parse `publish_info` as JSON.
4. Read `appmsgex[]` to build article rows.

Recommended row mapping:

- `account_name`: selected account nickname
- `account_alias`: selected account alias
- `fakeid`: selected account fakeid
- `article_title`: `appmsgex[].title`
- `publish_time`: prefer `appmsgex[].create_time`, fall back to `update_time`, convert unix timestamp to readable time
- `link`: `appmsgex[].link`
- `cover`: `appmsgex[].cover`
- `source`: `network`

## Verified First Page Example

For the target account selected in the live run, the dialog showed page `1 / 185` and the first visible titles included:

- an SEO data analysis article mentioning Raphael AI
- a February 2026 new-site competition champion recap
- an article about building an online mini game with Claude
- a February 2026 competition results article
- an OpenClaw meetup announcement

## DOM Fallback

If the response body cannot be accessed, read the visible list under the content selection area:

- title text rows
- date rows
- pager text such as `1 / 185`

In the verified session, the list rendered as alternating title/date rows in the dialog content. When using DOM fallback, return `source: "dom"` and say that links and covers may be incomplete.

## Pagination

The dialog exposes a next-page control and page jump controls.

When more than one page is needed:

1. Prefer changing the request parameters conceptually by following UI pagination.
2. If using DOM-driven MCP only, click the next-page control, then read the next response or page rows.
3. Report whether the result contains only the current page or multiple pages.

## Rate Limit Strategy

The backend rate-limits rapid pagination. In a live extraction run, fast consecutive requests eventually returned:

- `base_resp.ret = 200013`
- `base_resp.err_msg = "freq control"`

Use this strategy for bulk extraction:

1. Never request multiple pages in parallel.
2. Prefer a larger `count` such as `20` when the backend accepts it, because it reduces total request volume.
3. Add a short delay of about `300-500 ms` between successful page requests.
4. If `ret = 200013`, wait `15-20 seconds`, then retry the same `begin` offset.
5. Stop only after several repeated rate-limit hits on the same page, and report the last successful offset.

Recommended bulk loop:

1. Set `begin = 0`.
2. Request one page.
3. Parse `publish_page`.
4. Extract all `appmsgex[].link` values from that page.
5. Increment `begin` by `count`.
6. Sleep briefly.
7. Retry with backoff if the backend returns `freq control`.

## Bulk Extraction Notes

- Deduplicate links at the end of the run.
- Expect some parse skips if individual `publish_info` payloads are malformed or unexpectedly empty.
- Do not assume `total_count` equals the final unique link count. Multi-item publish records and repeated links can change the final number.
- For "export all links" tasks, prefer saving only links in the final file unless the user asked for metadata too.

## Failure Handling

- If login is not complete, stop.
- If the hyperlink toolbar item is not visible, confirm the page is the article editor and not the backend home page.
- If switching to another account returns no results, report the exact query used.
- If the account search is ambiguous, compare both nickname and alias before selecting.
- If bulk extraction hits repeated `freq control` responses, report that the backend is throttling the session and resume only after a cool-down window.
