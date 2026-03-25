#!/usr/bin/env python3
import argparse
import json
import os
from datetime import datetime, timezone
from pathlib import Path
from typing import Any, Dict, List


def now_iso() -> str:
    return datetime.now(timezone.utc).isoformat()


def default_base_dir() -> Path:
    override = os.environ.get('WEB_BACKLINKER_BASE_DIR')
    if override:
        return Path(override).expanduser()

    script_path = Path(__file__).resolve()
    if len(script_path.parents) >= 4 and script_path.parents[2].name == 'skills':
        return script_path.parents[3] / 'data' / 'web-backlinker'

    return Path('data') / 'web-backlinker'


def default_registry_path() -> Path:
    return default_base_dir() / 'accounts' / 'site-accounts.json'


def load_registry(path: Path) -> Dict[str, Any]:
    if not path.exists():
        return {'updated_at': '', 'records': []}
    data = json.loads(path.read_text(encoding='utf-8'))
    if isinstance(data, list):
        data = {'updated_at': '', 'records': data}
    data.setdefault('updated_at', '')
    data.setdefault('records', [])
    return data


def save_registry(path: Path, data: Dict[str, Any]) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    tmp = path.with_name(f'.{path.name}.tmp')
    tmp.write_text(json.dumps(data, ensure_ascii=False, indent=2) + '\n', encoding='utf-8')
    os.replace(tmp, path)


def normalize_record(record: Dict[str, Any]) -> Dict[str, Any]:
    normalized = dict(record)
    normalized['domain'] = str(normalized.get('domain', '')).strip().lower()
    normalized['account_ref'] = str(normalized.get('account_ref', '')).strip() or f"acct-{normalized['domain'].replace('.', '-') if normalized['domain'] else 'unknown'}"
    normalized['auth_type'] = str(normalized.get('auth_type', 'unknown')).strip() or 'unknown'
    normalized['signup_email'] = str(normalized.get('signup_email', '')).strip()
    normalized['username'] = str(normalized.get('username', '')).strip()
    normalized['credential_ref'] = str(normalized.get('credential_ref', '')).strip()
    normalized['browser_profile_ref'] = str(normalized.get('browser_profile_ref', '')).strip()
    normalized['created_at'] = str(normalized.get('created_at', '')).strip() or now_iso()
    normalized['last_verified_at'] = str(normalized.get('last_verified_at', '')).strip()
    normalized['status'] = str(normalized.get('status', 'active')).strip() or 'active'
    normalized['notes'] = [str(v) for v in normalized.get('notes', []) if str(v).strip()]
    return normalized


def upsert_record(data: Dict[str, Any], record: Dict[str, Any]) -> Dict[str, Any]:
    record = normalize_record(record)
    for idx, existing in enumerate(data['records']):
        if existing.get('domain') == record['domain']:
            merged = normalize_record({**existing, **record})
            data['records'][idx] = merged
            data['updated_at'] = now_iso()
            return merged
    data['records'].append(record)
    data['records'] = sorted([normalize_record(r) for r in data['records']], key=lambda r: r['domain'])
    data['updated_at'] = now_iso()
    return record


def find_record(data: Dict[str, Any], domain: str) -> Dict[str, Any]:
    key = domain.strip().lower()
    for record in data['records']:
        if record.get('domain') == key:
            return normalize_record(record)
    raise SystemExit(f'account not found for domain: {domain}')


def cmd_upsert(args):
    path = Path(args.registry).expanduser().resolve()
    data = load_registry(path)
    notes: List[str] = list(args.note or [])
    record = upsert_record(data, {
        'domain': args.domain,
        'account_ref': args.account_ref,
        'auth_type': args.auth_type,
        'signup_email': args.signup_email,
        'username': args.username,
        'credential_ref': args.credential_ref,
        'browser_profile_ref': args.browser_profile_ref,
        'created_at': args.created_at,
        'last_verified_at': args.last_verified_at,
        'status': args.status,
        'notes': notes,
    })
    save_registry(path, data)
    print(json.dumps({'ok': True, 'registry': str(path), 'record': record}, ensure_ascii=False, indent=2))


def cmd_get(args):
    path = Path(args.registry).expanduser().resolve()
    data = load_registry(path)
    print(json.dumps({'ok': True, 'record': find_record(data, args.domain)}, ensure_ascii=False, indent=2))


def cmd_list(args):
    path = Path(args.registry).expanduser().resolve()
    data = load_registry(path)
    records = [normalize_record(record) for record in data['records']]
    if args.auth_type:
        records = [record for record in records if record['auth_type'] == args.auth_type]
    if args.status:
        records = [record for record in records if record['status'] == args.status]
    print(json.dumps({'ok': True, 'count': len(records), 'records': records}, ensure_ascii=False, indent=2))


def cmd_touch_verified(args):
    path = Path(args.registry).expanduser().resolve()
    data = load_registry(path)
    record = find_record(data, args.domain)
    record['last_verified_at'] = args.at or now_iso()
    if args.status:
        record['status'] = args.status
    upsert_record(data, record)
    save_registry(path, data)
    print(json.dumps({'ok': True, 'registry': str(path), 'record': record}, ensure_ascii=False, indent=2))


def main() -> int:
    parser = argparse.ArgumentParser(description='Manage reusable per-domain site accounts for Web Backlinker.')
    parser.add_argument('--registry', default=str(default_registry_path()))
    sub = parser.add_subparsers(dest='cmd', required=True)

    p = sub.add_parser('upsert')
    p.add_argument('--domain', required=True)
    p.add_argument('--account-ref', default='')
    p.add_argument('--auth-type', default='unknown')
    p.add_argument('--signup-email', default='')
    p.add_argument('--username', default='')
    p.add_argument('--credential-ref', default='')
    p.add_argument('--browser-profile-ref', default='')
    p.add_argument('--created-at', default='')
    p.add_argument('--last-verified-at', default='')
    p.add_argument('--status', default='active')
    p.add_argument('--note', action='append')
    p.set_defaults(func=cmd_upsert)

    p = sub.add_parser('get')
    p.add_argument('--domain', required=True)
    p.set_defaults(func=cmd_get)

    p = sub.add_parser('list')
    p.add_argument('--auth-type', default='')
    p.add_argument('--status', default='')
    p.set_defaults(func=cmd_list)

    p = sub.add_parser('touch-verified')
    p.add_argument('--domain', required=True)
    p.add_argument('--at', default='')
    p.add_argument('--status', default='')
    p.set_defaults(func=cmd_touch_verified)

    args = parser.parse_args()
    args.func(args)
    return 0


if __name__ == '__main__':
    raise SystemExit(main())
