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

- 当前 WSL 环境下已恢复 Codex notify hook：
  - `notify = ["/home/gc/.codex/notify.py"]`
- Hook 脚本：`~/.codex/notify.py`
- 原始事件日志：`~/.codex/notify-events.jsonl`
- 唤醒日志：`~/.codex/notify-wake.log`
- 作用：Codex 高价值事件（完成/审批/错误）会通过 `openclaw system event --mode now` 立即唤醒主会话，减少 tmux 多 agent 轮询

