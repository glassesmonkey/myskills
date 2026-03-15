#!/usr/bin/env python3
import argparse
import json
import os
import uuid
from datetime import datetime, timedelta, timezone
from pathlib import Path


def now_iso() -> str:
    return datetime.now(timezone.utc).isoformat()


def load_json(path: Path):
    if not path.exists():
        raise SystemExit(f'file not found: {path}')
    return json.loads(path.read_text(encoding='utf-8'))


def save_json(path: Path, data):
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(data, ensure_ascii=False, indent=2) + '\n', encoding='utf-8')


def append_event(events_path: Path, event: dict):
    events_path.parent.mkdir(parents=True, exist_ok=True)
    with events_path.open('a', encoding='utf-8') as fh:
        fh.write(json.dumps(event, ensure_ascii=False) + '\n')


def parse_ts(value: str):
    if not value:
        return None
    try:
        return datetime.fromisoformat(value.replace('Z', '+00:00'))
    except Exception:
        return None


def cmd_init(args):
    input_path = Path(args.input_json).expanduser().resolve()
    out_path = Path(args.output).expanduser().resolve()
    events_path = Path(args.events).expanduser().resolve()
    payload = load_json(input_path)
    rows = payload.get('rows', payload)
    ts = now_iso()
    tasks = []
    for row in rows:
        task_id = row.get('task_id') or f"task-{row['row_id']}"
        tasks.append({
            'task_id': task_id,
            'row_id': row['row_id'],
            'domain': row['domain'],
            'input_url': row.get('input_url', ''),
            'normalized_url': row['normalized_url'],
            'status': 'PENDING',
            'phase': 'imported',
            'strategy': '',
            'attempts': 0,
            'last_error': '',
            'last_progress_at': ts,
            'updated_at': ts,
            'locked_by': '',
            'lock_expires_at': '',
            'playbook_id': '',
            'notes': [],
        })
    data = {
        'generated_at': ts,
        'count': len(tasks),
        'tasks': tasks,
    }
    save_json(out_path, data)
    append_event(events_path, {'ts': ts, 'action': 'init', 'count': len(tasks), 'taskStore': str(out_path)})
    print(json.dumps({'ok': True, 'count': len(tasks), 'output': str(out_path)}, ensure_ascii=False, indent=2))


def task_matches_filter(task, statuses):
    return not statuses or task['status'] in statuses


def cmd_claim(args):
    store_path = Path(args.store).expanduser().resolve()
    events_path = Path(args.events).expanduser().resolve()
    data = load_json(store_path)
    tasks = data['tasks']
    statuses = set(args.status or ['PENDING', 'READY', 'RETRYABLE'])
    ts = datetime.now(timezone.utc)
    chosen = None
    for task in tasks:
        if args.domain and task['domain'] != args.domain:
            continue
        if not task_matches_filter(task, statuses):
            continue
        lock_expires = parse_ts(task.get('lock_expires_at', ''))
        if task.get('locked_by') and lock_expires and lock_expires > ts:
            continue
        chosen = task
        break
    if chosen is None:
        print(json.dumps({'ok': False, 'claimed': None}, ensure_ascii=False, indent=2))
        return
    worker_id = args.worker_id or f'worker-{uuid.uuid4().hex[:8]}'
    chosen['status'] = 'RUNNING'
    chosen['phase'] = args.phase or chosen.get('phase') or 'running'
    chosen['attempts'] = int(chosen.get('attempts', 0)) + 1
    chosen['locked_by'] = worker_id
    chosen['lock_expires_at'] = (ts + timedelta(seconds=args.lock_seconds)).isoformat()
    chosen['last_progress_at'] = ts.isoformat()
    chosen['updated_at'] = ts.isoformat()
    save_json(store_path, data)
    append_event(events_path, {
        'ts': ts.isoformat(),
        'action': 'claim',
        'task_id': chosen['task_id'],
        'domain': chosen['domain'],
        'worker_id': worker_id,
        'lock_expires_at': chosen['lock_expires_at'],
    })
    print(json.dumps({'ok': True, 'claimed': chosen}, ensure_ascii=False, indent=2))


def find_task(data, task_id):
    for task in data['tasks']:
        if task['task_id'] == task_id or task['row_id'] == task_id or task['domain'] == task_id:
            return task
    raise SystemExit(f'task not found: {task_id}')


def cmd_checkpoint(args):
    store_path = Path(args.store).expanduser().resolve()
    events_path = Path(args.events).expanduser().resolve()
    data = load_json(store_path)
    task = find_task(data, args.task)
    ts = now_iso()
    if args.phase:
        task['phase'] = args.phase
    task['last_progress_at'] = ts
    task['updated_at'] = ts
    if args.note:
        task.setdefault('notes', []).append(args.note)
    if args.status:
        task['status'] = args.status
    if args.extend_lock_seconds and task.get('locked_by'):
        task['lock_expires_at'] = (datetime.now(timezone.utc) + timedelta(seconds=args.extend_lock_seconds)).isoformat()
    save_json(store_path, data)
    append_event(events_path, {
        'ts': ts,
        'action': 'checkpoint',
        'task_id': task['task_id'],
        'domain': task['domain'],
        'status': task['status'],
        'phase': task.get('phase', ''),
        'note': args.note or '',
    })
    print(json.dumps({'ok': True, 'task': task}, ensure_ascii=False, indent=2))


def cmd_finish(args):
    store_path = Path(args.store).expanduser().resolve()
    events_path = Path(args.events).expanduser().resolve()
    data = load_json(store_path)
    task = find_task(data, args.task)
    ts = now_iso()
    task['status'] = args.status
    if args.phase:
        task['phase'] = args.phase
    task['last_progress_at'] = ts
    task['updated_at'] = ts
    task['locked_by'] = ''
    task['lock_expires_at'] = ''
    if args.error:
        task['last_error'] = args.error
    if args.note:
        task.setdefault('notes', []).append(args.note)
    save_json(store_path, data)
    append_event(events_path, {
        'ts': ts,
        'action': 'finish',
        'task_id': task['task_id'],
        'domain': task['domain'],
        'status': task['status'],
        'phase': task.get('phase', ''),
        'error': args.error or '',
        'note': args.note or '',
    })
    print(json.dumps({'ok': True, 'task': task}, ensure_ascii=False, indent=2))


def cmd_summary(args):
    store_path = Path(args.store).expanduser().resolve()
    data = load_json(store_path)
    ts = datetime.now(timezone.utc)
    summary = {
        'generated_at': ts.isoformat(),
        'counts': {},
        'stalled': [],
        'running': [],
    }
    for task in data['tasks']:
        summary['counts'][task['status']] = summary['counts'].get(task['status'], 0) + 1
        if task['status'] == 'RUNNING':
            summary['running'].append({'task_id': task['task_id'], 'domain': task['domain'], 'phase': task.get('phase', '')})
            last = parse_ts(task.get('last_progress_at', ''))
            if last and (ts - last).total_seconds() >= args.stalled_seconds:
                summary['stalled'].append({
                    'task_id': task['task_id'],
                    'domain': task['domain'],
                    'phase': task.get('phase', ''),
                    'last_progress_at': task.get('last_progress_at', ''),
                })
    print(json.dumps(summary, ensure_ascii=False, indent=2))


def main():
    parser = argparse.ArgumentParser(description='Manage local Web Backlinker single-URL task state.')
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
    p.add_argument('--status', action='append', help='claimable statuses; repeatable')
    p.set_defaults(func=cmd_claim)

    p = sub.add_parser('checkpoint')
    p.add_argument('--store', required=True)
    p.add_argument('--events', required=True)
    p.add_argument('--task', required=True)
    p.add_argument('--phase', default='')
    p.add_argument('--status', default='')
    p.add_argument('--note', default='')
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
    p.set_defaults(func=cmd_finish)

    p = sub.add_parser('summary')
    p.add_argument('--store', required=True)
    p.add_argument('--stalled-seconds', type=int, default=300)
    p.set_defaults(func=cmd_summary)

    args = parser.parse_args()
    args.func(args)


if __name__ == '__main__':
    main()
