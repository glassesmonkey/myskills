#!/usr/bin/env python3
import json, os, sys
from datetime import datetime, timezone


def now_iso():
    return datetime.now(timezone.utc).astimezone().isoformat(timespec='seconds')


def slug(s: str) -> str:
    return ''.join(c.lower() if c.isalnum() else '-' for c in s).strip('-')


def main():
    if len(sys.argv) < 4:
        print('usage: init_run.py <task_type> <title> <goal>')
        sys.exit(1)

    task_type, title, goal = sys.argv[1], sys.argv[2], sys.argv[3]
    ts = datetime.now().strftime('%Y%m%d-%H%M%S')
    run_id = f"{slug(task_type)}-{ts}"

    base = '/home/gc/.openclaw/workspace/data/task-runtime'
    for sub in ['runs', 'events', 'briefs', 'leases', 'artifacts']:
        os.makedirs(os.path.join(base, sub), exist_ok=True)
    os.makedirs(os.path.join(base, 'artifacts', run_id), exist_ok=True)

    run = {
        'run_id': run_id,
        'task_type': task_type,
        'title': title,
        'goal': goal,
        'status': 'CREATED',
        'current_phase': 'init',
        'current_item': None,
        'last_good_checkpoint': None,
        'last_progress_at': None,
        'reason_code': None,
        'requires_human': False,
        'dependency_blocked': False,
        'resume_from': None,
        'next_action': 'set first executable phase',
        'created_at': now_iso(),
        'updated_at': now_iso()
    }

    with open(os.path.join(base, 'runs', f'{run_id}.json'), 'w', encoding='utf-8') as f:
        json.dump(run, f, ensure_ascii=False, indent=2)

    open(os.path.join(base, 'events', f'{run_id}.jsonl'), 'a', encoding='utf-8').close()

    brief = {
        'run_id': run_id,
        'goal': goal,
        'current_status': 'CREATED',
        'current_phase': 'init',
        'last_good_checkpoint': None,
        'recent_events': [],
        'resume_from': None,
        'next_action': 'set first executable phase',
        'hard_rules': ['do not rely on chat as the only state store']
    }
    with open(os.path.join(base, 'briefs', f'{run_id}.json'), 'w', encoding='utf-8') as f:
        json.dump(brief, f, ensure_ascii=False, indent=2)

    print(run_id)


if __name__ == '__main__':
    main()
