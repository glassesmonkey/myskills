#!/usr/bin/env python3
import argparse
import os
import re
from datetime import datetime, timezone
from pathlib import Path


def slugify(value: str) -> str:
    value = value.strip().lower()
    value = re.sub(r'[^a-z0-9.-]+', '-', value)
    value = re.sub(r'-+', '-', value).strip('-')
    return value or 'playbook'


def default_base_dir() -> Path:
    override = os.environ.get('WEB_BACKLINKER_BASE_DIR')
    if override:
        return Path(override).expanduser() / 'playbooks'

    script_path = Path(__file__).resolve()
    if len(script_path.parents) >= 4 and script_path.parents[2].name == 'skills':
        return script_path.parents[3] / 'data' / 'web-backlinker' / 'playbooks'

    return Path('data') / 'web-backlinker' / 'playbooks'


def main() -> int:
    parser = argparse.ArgumentParser(description='Create a Web Backlinker playbook stub.')
    parser.add_argument('--base-dir', default=str(default_base_dir()))
    parser.add_argument('--scope', choices=['site', 'pattern'], required=True)
    parser.add_argument('--name', required=True, help='Domain for site scope or family name for pattern scope')
    parser.add_argument('--site-type', default='unknown')
    parser.add_argument('--auth-type', default='unknown')
    parser.add_argument('--submission-type', default='unknown')
    parser.add_argument('--credential-ref', default='')
    parser.add_argument('--force', action='store_true')
    args = parser.parse_args()

    scope_dir = 'sites' if args.scope == 'site' else 'patterns'
    stem = slugify(args.name)
    out_dir = Path(args.base_dir).expanduser().resolve() / scope_dir
    out_dir.mkdir(parents=True, exist_ok=True)
    out_path = out_dir / f'{stem}.yaml'

    if out_path.exists() and not args.force:
        raise SystemExit(f'playbook already exists: {out_path} (use --force to overwrite)')

    now = datetime.now(timezone.utc).isoformat()
    playbook_id = f"{args.scope}-{stem}"
    body = f"""playbook_id: {playbook_id}
scope: {args.scope}
domain_or_family: {args.name}
site_type: {args.site_type}
auth_type: {args.auth_type}
submission_type: {args.submission_type}
version: 1
success_count: 0
last_success_at: null
credential_ref: {args.credential_ref or 'null'}
created_at: {now}
entrypoints:
  home: null
  login: null
  submit: null
steps:
  - step_index: 1
    action_type: inspect
    goal: capture the first reusable action
    locator_primary: null
    locator_fallback: null
    input_source: null
    success_signal: null
    failure_signal: null
    notes: fill after a successful run
success_signals: []
failure_signals: []
manual_touchpoints: []
notes:
  - scaffolded by web-backlinker
"""
    out_path.write_text(body, encoding='utf-8')
    print(out_path)
    return 0


if __name__ == '__main__':
    raise SystemExit(main())
