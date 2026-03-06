# TOOLS.md - Local Notes

Skills define _how_ tools work. This file is for _your_ specifics — the stuff that's unique to your setup.

## What Goes Here

Things like:

- Camera names and locations
- SSH hosts and aliases
- Preferred voices for TTS
- Speaker/room names
- Device nicknames
- Anything environment-specific

## Examples

```markdown
### Cameras

- living-room → Main area, 180° wide angle
- front-door → Entrance, motion-triggered

### SSH

- home-server → 192.168.1.100, user: admin

### TTS

- Preferred voice: "Nova" (warm, slightly British)
- Default speaker: Kitchen HomePod
```

## Why Separate?

Skills are shared. Your setup is yours. Keeping them apart means you can update skills without losing your notes, and share skills without leaking your infrastructure.

---

Add whatever helps you do your job. This is your cheat sheet.

### Notion

- Default parent page URL: https://www.notion.so/Open-Claw-31862cfa98a58050ab1eead05ea823df?source=copy_link
- Default parent page ID: 31862cfa-98a5-8050-ab1e-ead05ea823df
- Rule: create all future OpenClaw-written Notion pages under this parent unless user specifies another parent explicitly.

### Codex Notify

- 当前 WSL 环境下 **未配置** `~/.codex/config.toml` 的 `notify = [...]`
- `~/.codex/notify.py` 与 `~/.codex/notify.sh` 目前都不存在
- 若后续恢复通知钩子，需要重新创建脚本并写回 Codex 配置
- 事件日志路径 `/tmp/codex_notify.log` 仅在 hook 恢复后才有意义
- 用途：在 tmux 多 agent 监控里减少轮询

