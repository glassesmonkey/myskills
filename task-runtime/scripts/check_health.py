#!/usr/bin/env python3
import json, os, sys
from datetime import datetime, timezone


def parse_iso(s):
    if not s:
        return None
    return datetime.fromisoformat(s)


def main():
    if len(sys.argv) < 2:
        print('usage: check_health.py <run_id> [max_stale_seconds]')
        sys.exit(1)

    run_id = sys.argv[1]
    max_stale = int(sys.argv[2]) if len(sys.argv) > 2 else 900
    base = '/home/gc/.openclaw/workspace/data/task-runtime'

    run_path = os.path.join(base, 'runs', f'{run_id}.json')
    lease_path = os.path.join(base, 'leases', f'{run_id}.json')
    with open(run_path, 'r', encoding='utf-8') as f:
        run = json.load(f)

    now = datetime.now(timezone.utc).astimezone()
    updated = parse_iso(run.get('updated_at'))
    stale = True if not updated else (now - updated).total_seconds() > max_stale

    lease_state = None
    lease_expired = None
    if os.path.exists(lease_path):
        with open(lease_path, 'r', encoding='utf-8') as f:
            lease = json.load(f)
        lease_state = lease.get('state')
        exp = parse_iso(lease.get('expires_at'))
        lease_expired = True if exp and now > exp else False

    status = run.get('status')
    if status == 'WAITING_HUMAN':
        classification = 'WAITING_HUMAN'
    elif status == 'WAITING_EXTERNAL':
        classification = 'WAITING_EXTERNAL'
    elif run.get('dependency_blocked') or run.get('reason_code') in ('dependency_unavailable', 'browser_gateway_timeout'):
        classification = 'HALTED_DEPENDENCY'
    elif stale and (lease_state is None or lease_expired is True):
        classification = 'STALLED'
    else:
        classification = status

    print(json.dumps({
        'run_id': run_id,
        'classification': classification,
        'status': status,
        'stale': stale,
        'lease_state': lease_state,
        'lease_expired': lease_expired,
        'reason_code': run.get('reason_code'),
        'next_action': run.get('next_action'),
        'resume_from': run.get('resume_from')
    }, ensure_ascii=False, indent=2))


if __name__ == '__main__':
    main()
