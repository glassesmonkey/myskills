#!/usr/bin/env python3
import argparse
import json
from datetime import datetime, timezone
from pathlib import Path


def build_run_id(now: datetime) -> str:
    return f"wb-{now.strftime('%Y%m%d-%H%M%S')}"


def main() -> int:
    parser = argparse.ArgumentParser(description='Create Web Backlinker runtime directories and manifest.')
    parser.add_argument('--base-dir', default='/home/gc/.openclaw/workspace/data/web-backlinker')
    parser.add_argument('--run-id', default='')
    parser.add_argument('--campaign-name', default='')
    parser.add_argument('--sheet-url', default='')
    parser.add_argument('--promoted', default='')
    args = parser.parse_args()

    now = datetime.now(timezone.utc)
    run_id = args.run_id or build_run_id(now)
    base_dir = Path(args.base_dir).expanduser().resolve()

    runs_dir = base_dir / 'runs'
    artifacts_dir = base_dir / 'artifacts' / run_id
    playbooks_sites_dir = base_dir / 'playbooks' / 'sites'
    playbooks_patterns_dir = base_dir / 'playbooks' / 'patterns'
    profiles_dir = base_dir / 'product-profiles'

    for path in [runs_dir, artifacts_dir, playbooks_sites_dir, playbooks_patterns_dir, profiles_dir]:
        path.mkdir(parents=True, exist_ok=True)

    for sub in ['screenshots', 'html', 'notes']:
        (artifacts_dir / sub).mkdir(parents=True, exist_ok=True)

    manifest = {
        'run_id': run_id,
        'created_at': now.isoformat(),
        'campaign_name': args.campaign_name,
        'sheet_url': args.sheet_url,
        'promoted': args.promoted,
        'base_dir': str(base_dir),
        'runs_dir': str(runs_dir),
        'artifacts_dir': str(artifacts_dir),
        'playbooks_sites_dir': str(playbooks_sites_dir),
        'playbooks_patterns_dir': str(playbooks_patterns_dir),
        'product_profiles_dir': str(profiles_dir),
        'state': 'BOOTSTRAPPED',
    }

    manifest_path = runs_dir / f'{run_id}.json'
    manifest_path.write_text(json.dumps(manifest, ensure_ascii=False, indent=2) + '\n', encoding='utf-8')
    manifest['manifest_path'] = str(manifest_path)
    print(json.dumps(manifest, ensure_ascii=False, indent=2))
    return 0


if __name__ == '__main__':
    raise SystemExit(main())
