#!/usr/bin/env python3
import argparse
import json
import os
import uuid
from datetime import datetime, timedelta, timezone
from pathlib import Path
from typing import Any, Dict, Iterable, List, Optional, Tuple

NOTE_LIMIT = 8
LOCAL_SUMMARY_ORDER = [
    'PENDING',
    'READY',
    'SCOUTING',
    'RUNNING',
    'WAITING_EMAIL',
    'WAITING_HUMAN',
    'RETRYABLE',
    'STALLED',
    'DONE',
    'FAILED',
    'SKIPPED',
]
SHEET_SUMMARY_ORDER = [
    'submitted',
    'verified',
    'pending_email',
    'needs_human',
    'failed',
    'skipped',
    'pending',
    'stalled',
]
STATUS_PRIORITY = {
    'WAITING_EMAIL': 0,
    'RETRYABLE': 1,
    'READY': 2,
    'PENDING': 3,
    'IMPORTED': 4,
    'SCOUTING': 5,
    'STALLED': 6,
}
REASON_PENALTY = {
    'captcha': 90,
    'captcha_required': 90,
    'cloudflare_challenge': 80,
    'payment_required': 75,
    'backlink_required': 75,
    'phone_verification': 75,
    'manual_content_needed': 65,
    'oauth_scope_review': 75,
    'suspicious_site': 90,
    'unknown_flow': 60,
    'missing_config': 95,
    'login_failed': 45,
}


def now_utc() -> datetime:
    return datetime.now(timezone.utc)


def now_iso() -> str:
    return now_utc().isoformat()


def parse_ts(value: str):
    if not value:
        return None
    try:
        return datetime.fromisoformat(value.replace('Z', '+00:00'))
    except Exception:
        return None


def load_json(path: Path):
    if not path.exists():
        raise SystemExit(f'file not found: {path}')
    return json.loads(path.read_text(encoding='utf-8'))


def save_json(path: Path, data):
    path.parent.mkdir(parents=True, exist_ok=True)
    tmp = path.with_name(f'.{path.name}.tmp')
    tmp.write_text(json.dumps(data, ensure_ascii=False, indent=2) + '\n', encoding='utf-8')
    os.replace(tmp, path)


def append_event(events_path: Optional[Path], event: dict):
    if not events_path:
        return
    events_path.parent.mkdir(parents=True, exist_ok=True)
    with events_path.open('a', encoding='utf-8') as fh:
        fh.write(json.dumps(event, ensure_ascii=False) + '\n')


def coerce_int(value: Any, default: int = 0) -> int:
    try:
        return int(value)
    except Exception:
        return default


def trim_notes(notes: Iterable[str], limit: int = NOTE_LIMIT) -> List[str]:
    cleaned = [str(n) for n in notes if str(n).strip()]
    if len(cleaned) > limit:
        return cleaned[-limit:]
    return cleaned


def default_task_id(row: Dict[str, Any]) -> str:
    if row.get('task_id'):
        return row['task_id']
    if row.get('row_id'):
        return f"task-{row['row_id']}"
    if row.get('domain'):
        return f"task-{row['domain']}"
    return f"task-{uuid.uuid4().hex[:12]}"


def normalize_task(task: Dict[str, Any]) -> Dict[str, Any]:
    normalized = dict(task)
    normalized.setdefault('task_id', default_task_id(task))
    normalized.setdefault('row_id', '')
    normalized.setdefault('domain', '')
    normalized.setdefault('input_url', '')
    normalized.setdefault('normalized_url', '')
    normalized.setdefault('status', 'PENDING')
    normalized.setdefault('phase', 'imported')
    normalized.setdefault('strategy', '')
    normalized['attempts'] = coerce_int(normalized.get('attempts', 0), 0)
    normalized.setdefault('last_error', '')
    normalized.setdefault('reason_code', '')
    normalized.setdefault('route', '')
    normalized.setdefault('result_code', '')
    normalized.setdefault('artifact_ref', '')
    normalized.setdefault('sheet_status', '')
    normalized.setdefault('sheet_note', '')
    ts = normalized.get('updated_at') or normalized.get('last_progress_at') or now_iso()
    normalized.setdefault('last_progress_at', ts)
    normalized.setdefault('updated_at', ts)
    normalized.setdefault('locked_by', '')
    normalized.setdefault('lock_expires_at', '')
    normalized.setdefault('playbook_id', '')
    normalized['notes'] = trim_notes(normalized.get('notes', []))
    return normalized


def normalize_store(data: Dict[str, Any]) -> Dict[str, Any]:
    normalized = dict(data)
    normalized.setdefault('generated_at', now_iso())
    tasks = [normalize_task(task) for task in normalized.get('tasks', [])]
    normalized['tasks'] = tasks
    normalized['count'] = len(tasks)
    return normalized


def derive_lease_path(store_path: Path) -> Path:
    return store_path.with_name(f'{store_path.stem}-lease.json')


def load_store(path: Path) -> Dict[str, Any]:
    return normalize_store(load_json(path))


def save_store(path: Path, data: Dict[str, Any]):
    data = normalize_store(data)
    data['count'] = len(data.get('tasks', []))
    save_json(path, data)


def find_task(data: Dict[str, Any], task_id: str) -> Dict[str, Any]:
    for task in data['tasks']:
        if task['task_id'] == task_id or task['row_id'] == task_id or task['domain'] == task_id:
            return task
    raise SystemExit(f'task not found: {task_id}')


def append_note_to_task(task: Dict[str, Any], note: str):
    if not note:
        return
    task.setdefault('notes', [])
    task['notes'] = trim_notes([*task['notes'], note])


def is_locked(task: Dict[str, Any], now: Optional[datetime] = None) -> bool:
    now = now or now_utc()
    lock_expires = parse_ts(task.get('lock_expires_at', ''))
    return bool(task.get('locked_by')) and bool(lock_expires and lock_expires > now)


def local_counts(tasks: Iterable[Dict[str, Any]]) -> Dict[str, int]:
    counts: Dict[str, int] = {}
    for task in tasks:
        status = task.get('status', 'PENDING')
        counts[status] = counts.get(status, 0) + 1
    return counts


def sheet_bucket_for_task(task: Dict[str, Any]) -> str:
    explicit = (task.get('sheet_status') or '').strip().upper()
    if explicit:
        mapping = {
            'SUBMITTED': 'submitted',
            'VERIFIED': 'verified',
            'PENDING_EMAIL': 'pending_email',
            'NEEDS_HUMAN': 'needs_human',
            'FAILED': 'failed',
            'SKIPPED': 'skipped',
            'STALLED': 'stalled',
            'PENDING': 'pending',
            'IMPORTED': 'pending',
            'RUNNING': 'pending',
        }
        return mapping.get(explicit, 'pending')

    status = task.get('status', 'PENDING')
    if status == 'DONE':
        return 'submitted'
    if status == 'WAITING_EMAIL':
        return 'pending_email'
    if status == 'WAITING_HUMAN':
        return 'needs_human'
    if status == 'FAILED':
        return 'failed'
    if status == 'SKIPPED':
        return 'skipped'
    if status == 'STALLED':
        return 'stalled'
    return 'pending'


def sheet_counts(tasks: Iterable[Dict[str, Any]]) -> Dict[str, int]:
    counts = {key: 0 for key in SHEET_SUMMARY_ORDER}
    for task in tasks:
        counts[sheet_bucket_for_task(task)] = counts.get(sheet_bucket_for_task(task), 0) + 1
    return counts


def summarize_counts(tasks: Iterable[Dict[str, Any]]) -> Dict[str, Any]:
    tasks = list(tasks)
    local = local_counts(tasks)
    sheet = sheet_counts(tasks)
    running = []
    stalled = []
    now = now_utc()
    for task in tasks:
        if task['status'] == 'RUNNING':
            running.append({'task_id': task['task_id'], 'domain': task['domain'], 'phase': task.get('phase', '')})
        if task['status'] in {'RUNNING', 'SCOUTING'}:
            last = parse_ts(task.get('last_progress_at', ''))
            if last and (now - last).total_seconds() >= 300:
                stalled.append({
                    'task_id': task['task_id'],
                    'domain': task['domain'],
                    'phase': task.get('phase', ''),
                    'last_progress_at': task.get('last_progress_at', ''),
                })
    return {
        'generated_at': now.isoformat(),
        'local_counts': local,
        'sheet_counts': sheet,
        'running': running,
        'stalled_candidates': stalled,
    }


def candidate_priority_tuple(task: Dict[str, Any]) -> Tuple[int, int, int, float, str]:
    status = task.get('status', 'PENDING')
    reason = task.get('reason_code') or task.get('last_error') or ''
    bucket = STATUS_PRIORITY.get(status, 99)
    penalty = REASON_PENALTY.get(reason, 0)
    attempts = coerce_int(task.get('attempts', 0), 0)
    updated = parse_ts(task.get('updated_at', '')) or parse_ts(task.get('last_progress_at', ''))
    updated_key = updated.timestamp() if updated else 0.0
    domain = task.get('domain', '')
    return (bucket, penalty, attempts, updated_key, domain)


def next_candidates(tasks: Iterable[Dict[str, Any]], statuses: Optional[Iterable[str]] = None, limit: int = 3,
                    include_locked: bool = False) -> List[Dict[str, Any]]:
    statuses_set = set(statuses or ['WAITING_EMAIL', 'RETRYABLE', 'READY', 'PENDING'])
    now = now_utc()
    eligible = []
    for task in tasks:
        if task.get('status') not in statuses_set:
            continue
        if not include_locked and is_locked(task, now):
            continue
        eligible.append(task)
    return sorted(eligible, key=candidate_priority_tuple)[:limit]


def resolve_events_path(value: str) -> Optional[Path]:
    return Path(value).expanduser().resolve() if value else None


def resolve_lease_path(args) -> Path:
    if getattr(args, 'lease', ''):
        return Path(args.lease).expanduser().resolve()
    if getattr(args, 'store', ''):
        return derive_lease_path(Path(args.store).expanduser().resolve())
    raise SystemExit('either --lease or --store is required for lease operations')


def load_lease(path: Path) -> Dict[str, Any]:
    if not path.exists():
        return {
            'state': 'RELEASED',
            'owner_worker': '',
            'started_at': '',
            'heartbeat_at': '',
            'expires_at': '',
            'processed_count': 0,
            'last_task_id': '',
        }
    return load_json(path)


def lease_is_active(lease: Dict[str, Any], now: Optional[datetime] = None) -> bool:
    now = now or now_utc()
    expires = parse_ts(lease.get('expires_at', ''))
    return lease.get('state') == 'ACTIVE' and bool(expires and expires > now)


def cmd_init(args):
    input_path = Path(args.input_json).expanduser().resolve()
    out_path = Path(args.output).expanduser().resolve()
    events_path = Path(args.events).expanduser().resolve()
    payload = load_json(input_path)
    rows = payload.get('rows', payload)
    ts = now_iso()
    tasks = []
    for row in rows:
        task = normalize_task({
            'task_id': default_task_id(row),
            'row_id': row['row_id'],
            'domain': row['domain'],
            'input_url': row.get('input_url', ''),
            'normalized_url': row['normalized_url'],
            'status': 'PENDING',
            'phase': 'imported',
            'strategy': '',
            'attempts': 0,
            'last_error': '',
            'reason_code': '',
            'route': '',
            'result_code': '',
            'artifact_ref': '',
            'sheet_status': 'IMPORTED',
            'sheet_note': '',
            'last_progress_at': ts,
            'updated_at': ts,
            'locked_by': '',
            'lock_expires_at': '',
            'playbook_id': '',
            'notes': [],
        })
        tasks.append(task)
    data = {
        'generated_at': ts,
        'count': len(tasks),
        'tasks': tasks,
    }
    save_store(out_path, data)
    append_event(events_path, {'ts': ts, 'action': 'init', 'count': len(tasks), 'taskStore': str(out_path)})
    print(json.dumps({'ok': True, 'count': len(tasks), 'output': str(out_path)}, ensure_ascii=False, indent=2))


def cmd_claim(args):
    store_path = Path(args.store).expanduser().resolve()
    events_path = Path(args.events).expanduser().resolve()
    data = load_store(store_path)
    statuses = set(args.status or ['WAITING_EMAIL', 'RETRYABLE', 'READY', 'PENDING'])
    candidates = next_candidates(data['tasks'], statuses=statuses, limit=1, include_locked=False)
    if args.domain:
        candidates = [task for task in candidates if task['domain'] == args.domain]
        if not candidates:
            for task in data['tasks']:
                if task['domain'] == args.domain and task['status'] in statuses and not is_locked(task):
                    candidates = [task]
                    break
    if not candidates:
        print(json.dumps({'ok': False, 'claimed': None}, ensure_ascii=False, indent=2))
        return

    chosen = candidates[0]
    worker_id = args.worker_id or f'worker-{uuid.uuid4().hex[:8]}'
    ts = now_utc()
    chosen['status'] = 'RUNNING'
    chosen['phase'] = args.phase or chosen.get('phase') or 'running'
    chosen['attempts'] = coerce_int(chosen.get('attempts', 0), 0) + 1
    chosen['locked_by'] = worker_id
    chosen['lock_expires_at'] = (ts + timedelta(seconds=args.lock_seconds)).isoformat()
    chosen['last_progress_at'] = ts.isoformat()
    chosen['updated_at'] = ts.isoformat()
    if args.sheet_status:
        chosen['sheet_status'] = args.sheet_status
    save_store(store_path, data)
    append_event(events_path, {
        'ts': ts.isoformat(),
        'action': 'claim',
        'task_id': chosen['task_id'],
        'row_id': chosen.get('row_id', ''),
        'domain': chosen['domain'],
        'worker_id': worker_id,
        'phase': chosen.get('phase', ''),
        'lock_expires_at': chosen['lock_expires_at'],
    })
    print(json.dumps({'ok': True, 'claimed': chosen}, ensure_ascii=False, indent=2))


def cmd_checkpoint(args):
    store_path = Path(args.store).expanduser().resolve()
    events_path = Path(args.events).expanduser().resolve()
    data = load_store(store_path)
    task = find_task(data, args.task)
    ts = now_iso()
    if args.phase:
        task['phase'] = args.phase
    if args.status:
        task['status'] = args.status
    if args.note:
        append_note_to_task(task, args.note)
    if args.reason_code:
        task['reason_code'] = args.reason_code
    if args.route:
        task['route'] = args.route
    if args.result_code:
        task['result_code'] = args.result_code
    if args.artifact_ref:
        task['artifact_ref'] = args.artifact_ref
    if args.sheet_status:
        task['sheet_status'] = args.sheet_status
    if args.sheet_note:
        task['sheet_note'] = args.sheet_note
    task['last_progress_at'] = ts
    task['updated_at'] = ts
    if args.extend_lock_seconds and task.get('locked_by'):
        task['lock_expires_at'] = (now_utc() + timedelta(seconds=args.extend_lock_seconds)).isoformat()
    save_store(store_path, data)
    append_event(events_path, {
        'ts': ts,
        'action': 'checkpoint',
        'task_id': task['task_id'],
        'row_id': task.get('row_id', ''),
        'domain': task['domain'],
        'status': task['status'],
        'phase': task.get('phase', ''),
        'reason_code': task.get('reason_code', ''),
        'route': task.get('route', ''),
        'artifact_ref': task.get('artifact_ref', ''),
        'note': args.note or '',
    })
    print(json.dumps({'ok': True, 'task': task}, ensure_ascii=False, indent=2))


def cmd_finish(args):
    store_path = Path(args.store).expanduser().resolve()
    events_path = Path(args.events).expanduser().resolve()
    data = load_store(store_path)
    task = find_task(data, args.task)
    ts = now_iso()
    task['status'] = args.status
    if args.phase:
        task['phase'] = args.phase
    if args.error:
        task['last_error'] = args.error
    if args.note:
        append_note_to_task(task, args.note)
    if args.reason_code:
        task['reason_code'] = args.reason_code
    if args.route:
        task['route'] = args.route
    if args.result_code:
        task['result_code'] = args.result_code
    if args.artifact_ref:
        task['artifact_ref'] = args.artifact_ref
    if args.sheet_status:
        task['sheet_status'] = args.sheet_status
    if args.sheet_note:
        task['sheet_note'] = args.sheet_note
    task['last_progress_at'] = ts
    task['updated_at'] = ts
    task['locked_by'] = ''
    task['lock_expires_at'] = ''
    save_store(store_path, data)
    append_event(events_path, {
        'ts': ts,
        'action': 'finish',
        'task_id': task['task_id'],
        'row_id': task.get('row_id', ''),
        'domain': task['domain'],
        'status': task['status'],
        'phase': task.get('phase', ''),
        'error': args.error or '',
        'reason_code': task.get('reason_code', ''),
        'route': task.get('route', ''),
        'artifact_ref': task.get('artifact_ref', ''),
        'note': args.note or '',
    })
    print(json.dumps({'ok': True, 'task': task}, ensure_ascii=False, indent=2))


def cmd_summary(args):
    store_path = Path(args.store).expanduser().resolve()
    data = load_store(store_path)
    summary = summarize_counts(data['tasks'])
    stalled_seconds = args.stalled_seconds
    if stalled_seconds != 300:
        now = now_utc()
        stalled = []
        for task in data['tasks']:
            if task['status'] in {'RUNNING', 'SCOUTING'}:
                last = parse_ts(task.get('last_progress_at', ''))
                if last and (now - last).total_seconds() >= stalled_seconds:
                    stalled.append({
                        'task_id': task['task_id'],
                        'domain': task['domain'],
                        'phase': task.get('phase', ''),
                        'last_progress_at': task.get('last_progress_at', ''),
                    })
        summary['stalled_candidates'] = stalled
    print(json.dumps(summary, ensure_ascii=False, indent=2))


def cmd_next_candidates(args):
    store_path = Path(args.store).expanduser().resolve()
    data = load_store(store_path)
    statuses = args.status or ['WAITING_EMAIL', 'RETRYABLE', 'READY', 'PENDING']
    candidates = next_candidates(data['tasks'], statuses=statuses, limit=args.limit, include_locked=args.include_locked)
    rendered = []
    for task in candidates:
        score = candidate_priority_tuple(task)
        rendered.append({
            'task_id': task['task_id'],
            'row_id': task.get('row_id', ''),
            'domain': task.get('domain', ''),
            'status': task.get('status', ''),
            'phase': task.get('phase', ''),
            'attempts': task.get('attempts', 0),
            'reason_code': task.get('reason_code', ''),
            'route': task.get('route', ''),
            'playbook_id': task.get('playbook_id', ''),
            'artifact_ref': task.get('artifact_ref', ''),
            'updated_at': task.get('updated_at', ''),
            'selection_score': list(score),
        })
    print(json.dumps({
        'generated_at': now_iso(),
        'statuses': statuses,
        'count': len(rendered),
        'candidates': rendered,
    }, ensure_ascii=False, indent=2))


def cmd_lease_acquire(args):
    lease_path = resolve_lease_path(args)
    events_path = resolve_events_path(getattr(args, 'events', ''))
    lease = load_lease(lease_path)
    ts = now_utc()
    active = lease_is_active(lease, ts)
    owner = args.owner or args.worker_id or f'worker-{uuid.uuid4().hex[:8]}'
    if active and lease.get('owner_worker') != owner:
        print(json.dumps({'ok': False, 'lease': lease, 'reason': 'already_active'}, ensure_ascii=False, indent=2))
        return
    new_lease = {
        **lease,
        'state': 'ACTIVE',
        'owner_worker': owner,
        'started_at': lease.get('started_at') or ts.isoformat(),
        'heartbeat_at': ts.isoformat(),
        'expires_at': (ts + timedelta(seconds=args.ttl_seconds)).isoformat(),
        'processed_count': coerce_int(lease.get('processed_count', 0), 0),
        'last_task_id': lease.get('last_task_id', ''),
    }
    save_json(lease_path, new_lease)
    append_event(events_path, {
        'ts': ts.isoformat(),
        'action': 'lease_acquire',
        'owner_worker': owner,
        'lease_path': str(lease_path),
        'expires_at': new_lease['expires_at'],
    })
    print(json.dumps({'ok': True, 'lease': new_lease}, ensure_ascii=False, indent=2))


def cmd_lease_heartbeat(args):
    lease_path = resolve_lease_path(args)
    events_path = resolve_events_path(getattr(args, 'events', ''))
    lease = load_lease(lease_path)
    ts = now_utc()
    owner = args.owner
    if not lease_is_active(lease, ts) or lease.get('owner_worker') != owner:
        print(json.dumps({'ok': False, 'lease': lease, 'reason': 'not_owner_or_inactive'}, ensure_ascii=False, indent=2))
        return
    lease['heartbeat_at'] = ts.isoformat()
    lease['expires_at'] = (ts + timedelta(seconds=args.ttl_seconds)).isoformat()
    if args.last_task_id:
        lease['last_task_id'] = args.last_task_id
    if args.increment_processed:
        lease['processed_count'] = coerce_int(lease.get('processed_count', 0), 0) + args.increment_processed
    save_json(lease_path, lease)
    append_event(events_path, {
        'ts': ts.isoformat(),
        'action': 'lease_heartbeat',
        'owner_worker': owner,
        'lease_path': str(lease_path),
        'expires_at': lease['expires_at'],
        'last_task_id': lease.get('last_task_id', ''),
        'processed_count': lease.get('processed_count', 0),
    })
    print(json.dumps({'ok': True, 'lease': lease}, ensure_ascii=False, indent=2))


def cmd_lease_release(args):
    lease_path = resolve_lease_path(args)
    events_path = resolve_events_path(getattr(args, 'events', ''))
    lease = load_lease(lease_path)
    ts = now_utc()
    owner = args.owner
    if lease.get('owner_worker') and owner and lease.get('owner_worker') != owner:
        print(json.dumps({'ok': False, 'lease': lease, 'reason': 'not_owner'}, ensure_ascii=False, indent=2))
        return
    lease.update({
        'state': 'RELEASED',
        'heartbeat_at': ts.isoformat(),
        'expires_at': ts.isoformat(),
    })
    save_json(lease_path, lease)
    append_event(events_path, {
        'ts': ts.isoformat(),
        'action': 'lease_release',
        'owner_worker': lease.get('owner_worker', ''),
        'lease_path': str(lease_path),
    })
    print(json.dumps({'ok': True, 'lease': lease}, ensure_ascii=False, indent=2))


def cmd_lease_status(args):
    lease_path = resolve_lease_path(args)
    lease = load_lease(lease_path)
    print(json.dumps({
        'ok': True,
        'lease_path': str(lease_path),
        'active': lease_is_active(lease),
        'lease': lease,
    }, ensure_ascii=False, indent=2))


def main():
    parser = argparse.ArgumentParser(description='Manage local Web Backlinker task state and batch lease state.')
    sub = parser.add_subparsers(dest='cmd', required=True)

    p = sub.add_parser('init')
    p.add_argument('--input-json', required=True, help='normalize_targets.py JSON output')
    p.add_argument('--output', required=True)
    p.add_argument('--events', required=True)
    p.set_defaults(func=cmd_init)

    p = sub.add_parser('claim')
    p.add_argument('--store', required=True)
    p.add_argument('--events', required=True)
    p.add_argument('--worker-id', default='')
    p.add_argument('--lock-seconds', type=int, default=1200)
    p.add_argument('--phase', default='running')
    p.add_argument('--domain', default='')
    p.add_argument('--sheet-status', default='RUNNING')
    p.add_argument('--status', action='append', help='claimable statuses; repeatable')
    p.set_defaults(func=cmd_claim)

    p = sub.add_parser('checkpoint')
    p.add_argument('--store', required=True)
    p.add_argument('--events', required=True)
    p.add_argument('--task', required=True)
    p.add_argument('--phase', default='')
    p.add_argument('--status', default='')
    p.add_argument('--note', default='')
    p.add_argument('--reason-code', default='')
    p.add_argument('--route', default='')
    p.add_argument('--result-code', default='')
    p.add_argument('--artifact-ref', default='')
    p.add_argument('--sheet-status', default='')
    p.add_argument('--sheet-note', default='')
    p.add_argument('--extend-lock-seconds', type=int, default=0)
    p.set_defaults(func=cmd_checkpoint)

    p = sub.add_parser('finish')
    p.add_argument('--store', required=True)
    p.add_argument('--events', required=True)
    p.add_argument('--task', required=True)
    p.add_argument('--status', required=True)
    p.add_argument('--phase', default='')
    p.add_argument('--error', default='')
    p.add_argument('--note', default='')
    p.add_argument('--reason-code', default='')
    p.add_argument('--route', default='')
    p.add_argument('--result-code', default='')
    p.add_argument('--artifact-ref', default='')
    p.add_argument('--sheet-status', default='')
    p.add_argument('--sheet-note', default='')
    p.set_defaults(func=cmd_finish)

    p = sub.add_parser('summary')
    p.add_argument('--store', required=True)
    p.add_argument('--stalled-seconds', type=int, default=300)
    p.set_defaults(func=cmd_summary)

    p = sub.add_parser('next-candidates')
    p.add_argument('--store', required=True)
    p.add_argument('--limit', type=int, default=3)
    p.add_argument('--include-locked', action='store_true')
    p.add_argument('--status', action='append', help='candidate statuses; repeatable')
    p.set_defaults(func=cmd_next_candidates)

    p = sub.add_parser('lease-acquire')
    p.add_argument('--store', default='')
    p.add_argument('--lease', default='')
    p.add_argument('--events', default='')
    p.add_argument('--owner', default='')
    p.add_argument('--worker-id', default='')
    p.add_argument('--ttl-seconds', type=int, default=1200)
    p.set_defaults(func=cmd_lease_acquire)

    p = sub.add_parser('lease-heartbeat')
    p.add_argument('--store', default='')
    p.add_argument('--lease', default='')
    p.add_argument('--events', default='')
    p.add_argument('--owner', required=True)
    p.add_argument('--ttl-seconds', type=int, default=1200)
    p.add_argument('--last-task-id', default='')
    p.add_argument('--increment-processed', type=int, default=0)
    p.set_defaults(func=cmd_lease_heartbeat)

    p = sub.add_parser('lease-release')
    p.add_argument('--store', default='')
    p.add_argument('--lease', default='')
    p.add_argument('--events', default='')
    p.add_argument('--owner', default='')
    p.set_defaults(func=cmd_lease_release)

    p = sub.add_parser('lease-status')
    p.add_argument('--store', default='')
    p.add_argument('--lease', default='')
    p.set_defaults(func=cmd_lease_status)

    args = parser.parse_args()
    args.func(args)


if __name__ == '__main__':
    main()
