#!/usr/bin/env python3
import json, os, sys
from datetime import datetime, timezone


def now_iso():
    return datetime.now(timezone.utc).astimezone().isoformat(timespec='seconds')


def main():
    if len(sys.argv) < 4:
        print('usage: update_run.py <run_id> <field> <value> [<field> <value> ...]')
        sys.exit(1)

    run_id = sys.argv[1]
    pairs = sys.argv[2:]
    if len(pairs) % 2 != 0:
        print('field/value pairs required')
        sys.exit(1)

    path = f'/home/gc/.openclaw/workspace/data/task-runtime/runs/{run_id}.json'
    with open(path, 'r', encoding='utf-8') as f:
        run = json.load(f)

    for i in range(0, len(pairs), 2):
        field, value = pairs[i], pairs[i+1]
        if value == 'null':
            value = None
        elif value == 'true':
            value = True
        elif value == 'false':
            value = False
        run[field] = value

    run['updated_at'] = now_iso()
    if run.get('status') == 'RUNNING':
        run['last_progress_at'] = now_iso()

    with open(path, 'w', encoding='utf-8') as f:
        json.dump(run, f, ensure_ascii=False, indent=2)

    print(path)


if __name__ == '__main__':
    main()
