# Resume Protocol (v1)

A resumable task must answer four questions clearly:

1. What was the last good checkpoint?
2. Why did progress stop?
3. What must be checked before resuming?
4. From exactly where should execution continue?

## Minimum resume payload

```json
{
  "last_good_checkpoint": "article 111 persisted",
  "reason_code": "browser_gateway_timeout",
  "resume_from": "article 112 / phase=detail.open",
  "next_action": "restore browser/gateway, then continue from 112"
}
```

## Rules

- Resume from explicit checkpoints, not from chat memory.
- If dependency health is unknown, check dependency first.
- If the blocker is human-owned, do not pretend automatic resume is safe.
- If state is stale and evidence is missing, prefer a cautious `READY` or `STALLED` recovery path over claiming active execution.

## Example: WeChat rebuild

Bad recovery:
- “Continue the old task”

Good recovery:
- “Last good checkpoint is article 111 persisted. Browser/gateway timed out after a waiting window. First restore browser/gateway health, then continue from article 112 in `detail.open`.”
