# Upstream audit — `eze-is/web-access`

Date: 2026-03-23  
Source: GitHub (`https://github.com/eze-is/web-access`)

## Files reviewed

All non-git source files in the upstream repo were reviewed:
- `README.md`
- `SKILL.md`
- `references/cdp-api.md`
- `scripts/cdp-proxy.mjs`
- `scripts/check-deps.sh`
- `scripts/match-site.sh`

## Skill vetting report

```text
SKILL VETTING REPORT
═══════════════════════════════════════
Skill: web-access
Source: GitHub
Author: eze-is / 一泽Eze
Version: repo docs show 2.x line
───────────────────────────────────────
METRICS:
• Stars: 88
• Forks: 12
• Last Updated: 2026-03-23
• Files Reviewed: 6
───────────────────────────────────────
RED FLAGS:
• No obvious secret exfiltration found
• No reads of ~/.ssh, ~/.aws, MEMORY.md, USER.md, SOUL.md, or IDENTITY.md found
• Raw upstream can control the user's real Chrome and operate inside logged-in sessions
• Raw upstream exposes a localhost HTTP control server (127.0.0.1:3456)
• Upstream instructions encourage optional use of Jina (third-party external service)

PERMISSIONS NEEDED:
• Files: DevToolsActivePort, local screenshots/logs, site pattern files
• Network: localhost CDP/HTTP control, target websites opened by browser, optional Jina
• Commands: bash, node, curl, pkill
───────────────────────────────────────
RISK LEVEL: 🟡 MEDIUM for code review, but effectively 🔴 HIGH if raw-installed into a high-trust agent because it can drive the user's logged-in browser

VERDICT: ⚠️ DO NOT RAW-INSTALL INTO OPENCLAW; PORT THE PHILOSOPHY, MAP EXECUTION TO OPENCLAW NATIVE TOOLS

NOTES:
• Main issue is not malware; main issue is architectural mismatch.
• Upstream is deeply tied to Claude Code paths and shell/CDP glue.
═══════════════════════════════════════
```

## Why this was ported instead of copied

The upstream design is valuable, but its implementation is Claude Code specific:
- skill path assumes `~/.claude/skills/web-access`
- browser control assumes a custom local CDP proxy on `localhost:3456`
- examples and control flow assume shell + `curl` as the execution substrate

OpenClaw already has first-class tools for these jobs. Recreating the upstream stack would add an unnecessary second browser-control layer, duplicate failure modes, and bypass some of OpenClaw's built-in ergonomics.

## Safe adaptation principle

Keep these parts:
- goal-directed web strategy
- search / read / browser tiering
- sub-agent parallelization
- per-domain site-pattern accumulation

Replace these parts:
- `WebSearch` / `WebFetch` / `curl` shell glue → OpenClaw `web_search` / `web_fetch`
- local CDP proxy → OpenClaw `browser`
- Claude Code sub-agent assumptions → OpenClaw `sessions_spawn`
- `~/.claude/skills/...` paths → workspace skill paths
