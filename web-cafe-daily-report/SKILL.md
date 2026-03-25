---
name: web-cafe-daily-report
description: Summarize the previous day's messages from the 1-12 Web.Cafe export-tool group chats at https://new.web.cafe/messages using a fixed logged-in Chrome profile and page-context API calls. Use when the user asks for a Web.Cafe 群日报, wants to collect/summarize yesterday's group-chat highlights, needs to refresh the group-id mapping, or wants a cron-friendly workflow that fetches prior-day history and produces a per-group daily brief plus overall summary.
---

# Web Cafe Daily Report

Use this skill to pull prior-day chat history from the Web.Cafe messages page and turn it into a concise daily brief.

## Workflow

1. Ensure the dedicated Chrome profile is running.
2. Refresh the group mapping if it is missing or stale.
3. Fetch the target day's messages for each mapped group.
4. Read the generated JSON.
5. Write a concise日报:
   - `1群：...`
   - `2群：...`
   - ...
   - `总结：...`
6. For each group, include 1-3 short original quotes when they materially support the takeaway.

Default target day: yesterday in `Asia/Shanghai`.

## Scripts

### 1) Launch / reuse the fixed profile

Use:

```bash
python3 skills/web-cafe-daily-report/scripts/launch_web_cafe_profile.py
```

Defaults:
- Chrome profile: `C:\Users\Administrator\AppData\Local\OpenClawProfiles\web-cafe-daily`
- Remote debugging port: `19223`
- URL: `https://new.web.cafe/messages`

### 2) Discover / refresh group mapping

Use when `references/group-map.json` does not exist, when the site changed, or when room ids look stale.

```bash
python3 skills/web-cafe-daily-report/scripts/discover_groups.py
```

This writes:
- `skills/web-cafe-daily-report/references/group-map.json`

The mapping contains:
- group index
- visible label
- `room_id`
- `wechat_wxid`
- `email`

### 3) Fetch one day's messages

Prefer this script:

```bash
python3 skills/web-cafe-daily-report/scripts/generate_daily_json.py --date 2026-03-23
```

Default output:
- `tmp/web-cafe-daily/YYYY-MM-DD.json`

The script:
- reuses the logged-in browser session
- calls `/api/community/message/load-message` from page context
- paginates backward with `is_after:false` and `time`
- keeps only messages whose `pub_time` falls on the requested Shanghai date
- is intended to be the cron-facing fetch step

## How to summarize

After fetching, read the JSON file and summarize only signal, not noise.
Use short original quotes to anchor important claims, e.g. `原话：哥飞说“...”` or `原话：某群友提到“...”`.

Prioritize:
- new tools / useful URLs
- platform policy/payment/account changes
- traffic/acquisition/distribution tactics
- monetization/pricing observations
- operational problems with clear lessons
- repeated consensus or strong disagreement worth tracking

De-prioritize:
- greetings
- one-line banter
- duplicate screenshots with no insight
- repetitive back-and-forth unless it reveals a real conclusion

## Output format

Use this shape:

```markdown
1群：
- 点1
- 点2
- 原话：某某说“...”

2群：
- 点1
- 原话：某某说“...”

...

总结：
- 总体趋势1
- 总体趋势2
- 值得明天继续盯的点
```

If a group has no meaningful signal, say:

- `无明显值得关注的信息`

## Notes

- Treat `pub_time` as the reporting date anchor.
- If the fetched JSON is empty for all groups, verify login state first, then refresh mapping.
- If only one or two groups fail, refresh mapping before assuming the site changed globally.
- For cron, prefer an isolated `agentTurn` that asks the agent to use this skill, run `fetch_day.py` for yesterday, and announce the rendered日报.
