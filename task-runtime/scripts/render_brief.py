#!/usr/bin/env python3
import json, os, sys


def main():
    if len(sys.argv) < 2:
        print('usage: render_brief.py <run_id>')
        sys.exit(1)

    run_id = sys.argv[1]
    base = '/home/gc/.openclaw/workspace/data/task-runtime'
    run_path = os.path.join(base, 'runs', f'{run_id}.json')
    events_path = os.path.join(base, 'events', f'{run_id}.jsonl')
    brief_path = os.path.join(base, 'briefs', f'{run_id}.json')

    with open(run_path, 'r', encoding='utf-8') as f:
        run = json.load(f)

    recent = []
    if os.path.exists(events_path):
        with open(events_path, 'r', encoding='utf-8') as f:
            lines = [line.strip() for line in f if line.strip()]
        for line in lines[-5:]:
            try:
                evt = json.loads(line)
                recent.append(evt.get('message'))
            except Exception:
                pass

    brief = {
        'run_id': run['run_id'],
        'goal': run.get('goal'),
        'current_status': run.get('status'),
        'current_phase': run.get('current_phase'),
        'last_good_checkpoint': run.get('last_good_checkpoint'),
        'recent_events': recent,
        'resume_from': run.get('resume_from'),
        'next_action': run.get('next_action'),
        'hard_rules': [
            'do not rely on stale business status files alone',
            'resume from explicit checkpoints only'
        ]
    }

    with open(brief_path, 'w', encoding='utf-8') as f:
        json.dump(brief, f, ensure_ascii=False, indent=2)

    print(brief_path)


if __name__ == '__main__':
    main()
