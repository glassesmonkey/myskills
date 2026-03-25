#!/usr/bin/env python3
import json, sys
from datetime import datetime, timezone


def now_iso():
    return datetime.now(timezone.utc).astimezone().isoformat(timespec='seconds')


def main():
    if len(sys.argv) < 4:
        print('usage: append_event.py <run_id> <type> <message> [phase] [item] [reason_code] [artifact_ref]')
        sys.exit(1)

    run_id = sys.argv[1]
    evt_type = sys.argv[2]
    message = sys.argv[3]
    phase = sys.argv[4] if len(sys.argv) > 4 else None
    item = sys.argv[5] if len(sys.argv) > 5 else None
    reason_code = sys.argv[6] if len(sys.argv) > 6 else None
    artifact_ref = sys.argv[7] if len(sys.argv) > 7 else None

    event = {
        'event_id': f'{run_id}-{int(datetime.now().timestamp())}',
        'run_id': run_id,
        'timestamp': now_iso(),
        'type': evt_type,
        'phase': phase,
        'item': item,
        'message': message,
        'reason_code': reason_code,
        'artifact_ref': artifact_ref,
    }

    path = f'/home/gc/.openclaw/workspace/data/task-runtime/events/{run_id}.jsonl'
    with open(path, 'a', encoding='utf-8') as f:
        f.write(json.dumps(event, ensure_ascii=False) + '\n')

    print(path)


if __name__ == '__main__':
    main()
