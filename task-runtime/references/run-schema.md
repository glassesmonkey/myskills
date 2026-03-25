# Run Schema (v1)

## Canonical runtime layout

```text
data/task-runtime/
  runs/
    <run-id>.json
  events/
    <run-id>.jsonl
  briefs/
    <run-id>.json
  leases/
    <run-id>.json
  artifacts/
    <run-id>/
```

## Run file

Recommended minimum fields:

```json
{
  "run_id": "task-20260322-001",
  "task_type": "wechat_article_rebuild",
  "title": "Rebuild target WeChat article archive",
  "goal": "Capture, clean, and persist all target articles",
  "status": "RUNNING",
  "current_phase": "article.list.fetch",
  "current_item": "111",
  "last_good_checkpoint": "article 111 persisted",
  "last_progress_at": "2026-03-22T09:10:00+08:00",
  "reason_code": null,
  "requires_human": false,
  "dependency_blocked": false,
  "resume_from": "article 112 / phase=detail.open",
  "next_action": "continue fetch from article 112",
  "created_at": "2026-03-22T09:00:00+08:00",
  "updated_at": "2026-03-22T09:10:00+08:00"
}
```

## Event log

Append-only JSONL. One meaningful event per line.

Recommended fields:

```json
{
  "event_id": "evt-001",
  "run_id": "task-20260322-001",
  "timestamp": "2026-03-22T09:10:00+08:00",
  "type": "checkpoint",
  "phase": "article.content.capture",
  "item": "111",
  "message": "article 111 captured and written",
  "reason_code": null,
  "artifact_ref": "artifacts/task-20260322-001/article-111.json"
}
```

## Brief file

Compact handoff summary for the next worker / recovery step.

Recommended fields:

```json
{
  "run_id": "task-20260322-001",
  "goal": "Capture, clean, and persist all target articles",
  "current_status": "STALLED",
  "current_phase": "article.list.fetch",
  "last_good_checkpoint": "article 111 persisted",
  "recent_events": ["browser timeout after wait window"],
  "resume_from": "article 112 / phase=detail.open",
  "next_action": "restore browser/gateway, then continue from 112",
  "hard_rules": ["do not claim active progress from stale status files"]
}
```

## Lease file

Optional in v1, but recommended.

```json
{
  "run_id": "task-20260322-001",
  "owner_worker": "worker-abc",
  "heartbeat_at": "2026-03-22T09:10:00+08:00",
  "expires_at": "2026-03-22T09:15:00+08:00",
  "state": "ACTIVE"
}
```
