#!/usr/bin/env python3
import argparse
import json
import os
from datetime import datetime, timezone
from pathlib import Path
from typing import Any, Dict, List

import yaml


def now_iso() -> str:
    return datetime.now(timezone.utc).isoformat()


def default_base_dir() -> Path:
    override = os.environ.get('WEB_BACKLINKER_BASE_DIR')
    if override:
        return Path(override).expanduser() / 'playbooks'

    script_path = Path(__file__).resolve()
    if len(script_path.parents) >= 4 and script_path.parents[2].name == 'skills':
        return script_path.parents[3] / 'data' / 'web-backlinker' / 'playbooks'

    return Path('data') / 'web-backlinker' / 'playbooks'


def slugify(value: str) -> str:
    return ''.join(ch.lower() if ch.isalnum() or ch in '.-' else '-' for ch in value).strip('-') or 'playbook'


def default_playbook_path(base_dir: Path, scope: str, name: str) -> Path:
    folder = 'sites' if scope == 'site' else 'patterns'
    return base_dir / folder / f'{slugify(name)}.yaml'


def load_playbook(path: Path) -> Dict[str, Any]:
    if not path.exists():
        return {}
    return yaml.safe_load(path.read_text(encoding='utf-8')) or {}


def parse_json_arg(value: str, default):
    if not value:
        return default
    return json.loads(value)


def merge_notes(existing: List[str], new_notes: List[str]) -> List[str]:
    merged = [str(n) for n in existing if str(n).strip()]
    for note in new_notes:
        if str(note).strip():
            merged.append(str(note))
    return merged[-12:]


def main() -> int:
    parser = argparse.ArgumentParser(description='Create or update a Web Backlinker site playbook with direct-execution fields.')
    parser.add_argument('--base-dir', default=str(default_base_dir()))
    parser.add_argument('--scope', choices=['site', 'pattern'], default='site')
    parser.add_argument('--name', required=True, help='Domain for site scope or family name for pattern scope')
    parser.add_argument('--playbook-path', default='')
    parser.add_argument('--site-type', default='unknown')
    parser.add_argument('--auth-type', default='unknown')
    parser.add_argument('--submission-type', default='unknown')
    parser.add_argument('--execution-mode', default='native')
    parser.add_argument('--automation-disposition', default='ASSISTED_EXECUTE')
    parser.add_argument('--fallback-route', default='native_submit')
    parser.add_argument('--credential-ref', default='')
    parser.add_argument('--account-ref', default='')
    parser.add_argument('--browser-profile-ref', default='')
    parser.add_argument('--stability-score', type=float, default=0.0)
    parser.add_argument('--replay-confidence', type=float, default=0.0)
    parser.add_argument('--last-validated-at', default='')
    parser.add_argument('--entry-home', default='')
    parser.add_argument('--entry-login', default='')
    parser.add_argument('--entry-submit', default='')
    parser.add_argument('--field-map-json', default='{}')
    parser.add_argument('--direct-steps-json', default='[]')
    parser.add_argument('--result-checks-json', default='{}')
    parser.add_argument('--success-signals-json', default='[]')
    parser.add_argument('--failure-signals-json', default='[]')
    parser.add_argument('--manual-touchpoints-json', default='[]')
    parser.add_argument('--note', action='append')
    args = parser.parse_args()

    base_dir = Path(args.base_dir).expanduser().resolve()
    playbook_path = Path(args.playbook_path).expanduser().resolve() if args.playbook_path else default_playbook_path(base_dir, args.scope, args.name)
    playbook_path.parent.mkdir(parents=True, exist_ok=True)
    current = load_playbook(playbook_path)
    ts = now_iso()

    updated = {
        'playbook_id': current.get('playbook_id') or f"{args.scope}-{slugify(args.name)}",
        'scope': args.scope,
        'domain_or_family': args.name,
        'domain': args.name if args.scope == 'site' else current.get('domain', ''),
        'site_type': args.site_type or current.get('site_type', 'unknown'),
        'auth_type': args.auth_type or current.get('auth_type', 'unknown'),
        'submission_type': args.submission_type or current.get('submission_type', 'unknown'),
        'version': int(current.get('version', 1)),
        'success_count': int(current.get('success_count', 0)),
        'last_success_at': current.get('last_success_at'),
        'credential_ref': args.credential_ref or current.get('credential_ref'),
        'account_ref': args.account_ref or current.get('account_ref'),
        'browser_profile_ref': args.browser_profile_ref or current.get('browser_profile_ref'),
        'execution_mode': args.execution_mode or current.get('execution_mode', 'native'),
        'automation_disposition': args.automation_disposition or current.get('automation_disposition', 'ASSISTED_EXECUTE'),
        'stability_score': args.stability_score if args.stability_score else float(current.get('stability_score', 0.0) or 0.0),
        'replay_confidence': args.replay_confidence if args.replay_confidence else float(current.get('replay_confidence', 0.0) or 0.0),
        'last_validated_at': args.last_validated_at or current.get('last_validated_at'),
        'created_at': current.get('created_at') or ts,
        'updated_at': ts,
        'entrypoints': {
            'home': args.entry_home or current.get('entrypoints', {}).get('home'),
            'login': args.entry_login or current.get('entrypoints', {}).get('login'),
            'submit': args.entry_submit or current.get('entrypoints', {}).get('submit'),
        },
        'steps': current.get('steps', []),
        'direct_steps': parse_json_arg(args.direct_steps_json, current.get('direct_steps', [])),
        'field_map': parse_json_arg(args.field_map_json, current.get('field_map', {})),
        'result_checks': parse_json_arg(args.result_checks_json, current.get('result_checks', {})),
        'success_signals': parse_json_arg(args.success_signals_json, current.get('success_signals', [])),
        'failure_signals': parse_json_arg(args.failure_signals_json, current.get('failure_signals', [])),
        'manual_touchpoints': parse_json_arg(args.manual_touchpoints_json, current.get('manual_touchpoints', [])),
        'fallback_route': args.fallback_route or current.get('fallback_route', 'native_submit'),
        'notes': merge_notes(current.get('notes', []), list(args.note or [])),
    }

    playbook_path.write_text(yaml.safe_dump(updated, allow_unicode=True, sort_keys=False), encoding='utf-8')
    print(json.dumps({'ok': True, 'playbook_path': str(playbook_path), 'execution_mode': updated['execution_mode']}, ensure_ascii=False, indent=2))
    return 0


if __name__ == '__main__':
    raise SystemExit(main())
