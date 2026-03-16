#!/usr/bin/env python3
import argparse
import json
import sys
from datetime import datetime, timezone
from pathlib import Path
from typing import Any, Dict, List, Optional

SCRIPT_DIR = Path(__file__).resolve().parent
if str(SCRIPT_DIR) not in sys.path:
    sys.path.insert(0, str(SCRIPT_DIR))

from task_store import (  # noqa: E402
    candidate_priority_tuple,
    derive_lease_path,
    load_json,
    load_lease,
    load_store,
    next_candidates,
    parse_ts,
    sheet_counts,
    lease_is_active,
)

PRODUCT_PROFILE_KEYS = [
    'product_name',
    'canonical_url',
    'one_liner',
    'short_description',
    'founded_year',
    'launch_date',
    'based_in_city',
    'based_in_region',
    'based_in_country',
    'submitter_name',
    'submitter_first_name',
    'submitter_last_name',
    'submitter_phone',
    'founder_name',
    'category_primary',
    'category_secondary',
    'pricing_model',
    'safe_claims',
    'not_supported',
]
HARD_RULES = [
    'Do not pay, reciprocate backlinks, or attempt CAPTCHA bypasses.',
    'Do not invent product claims; use the product profile as the source of truth.',
    'Park the row quickly as WAITING_HUMAN when auth, phone, payment, CAPTCHA, Cloudflare, or manual-content blockers appear.',
    'At most one deep submit path per worker run; other slots should stay lightweight scout/triage work.',
]


def now_iso() -> str:
    return datetime.now(timezone.utc).isoformat()


def default_output_path(store_path: Path) -> Path:
    stem = store_path.stem
    if stem.endswith('-current-run'):
        stem = stem[:-12]
    return store_path.with_name(f'{stem}-worker-brief.json')


def tail_jsonl(path: Path, limit: int) -> List[Dict[str, Any]]:
    if not path.exists() or limit <= 0:
        return []
    lines = path.read_text(encoding='utf-8').splitlines()
    items: List[Dict[str, Any]] = []
    for line in lines[-limit:]:
        try:
            items.append(json.loads(line))
        except Exception:
            continue
    return items


def minimal_product_profile(path: Path) -> Dict[str, Any]:
    raw = load_json(path)
    result = {key: raw.get(key) for key in PRODUCT_PROFILE_KEYS if key in raw}
    result['contact_email_policy'] = {
        'default_product_contact': 'support@exactstatement.com',
        'prefer_company_email_when_required': 'admin@exactstatement.com',
        'personal_fallback': 'alexfefun1@gmail.com',
    }
    artifacts = raw.get('artifacts', {}) or {}
    if artifacts.get('homepage_screenshot'):
        result['homepage_screenshot'] = artifacts['homepage_screenshot']
    return result


def playbook_path_for(domain: str, playbooks_dir: Optional[Path]) -> Optional[Path]:
    if not playbooks_dir or not domain:
        return None
    candidates = [domain]
    if domain.startswith('www.'):
        candidates.append(domain[4:])
    for candidate in candidates:
        path = playbooks_dir / f'{candidate}.yaml'
        if path.exists():
            return path
    return None


def estimated_friction(task: Dict[str, Any]) -> str:
    reason = (task.get('reason_code') or task.get('last_error') or '').strip()
    if task.get('status') == 'WAITING_EMAIL':
        return 'medium'
    if reason in {'captcha', 'captcha_required', 'cloudflare_challenge', 'payment_required', 'phone_verification'}:
        return 'high'
    if reason in {'manual_content_needed', 'oauth_scope_review', 'backlink_required'}:
        return 'medium-high'
    if task.get('status') == 'RETRYABLE':
        return 'medium'
    return 'low'


def submit_likelihood(task: Dict[str, Any], has_playbook: bool) -> str:
    status = task.get('status')
    reason = (task.get('reason_code') or task.get('last_error') or '').strip()
    if status == 'WAITING_EMAIL':
        return 'high'
    if reason in {'captcha', 'captcha_required', 'cloudflare_challenge', 'payment_required', 'manual_content_needed'}:
        return 'low'
    if has_playbook and status in {'RETRYABLE', 'READY', 'PENDING'}:
        return 'medium-high'
    if status == 'RETRYABLE':
        return 'medium'
    return 'medium'


def selection_reasons(task: Dict[str, Any], has_playbook: bool) -> List[str]:
    reasons = [f"priority:{task.get('status', 'PENDING').lower()}"]
    if has_playbook:
        reasons.append('playbook:available')
    reason_code = (task.get('reason_code') or task.get('last_error') or '').strip()
    if reason_code:
        reasons.append(f'reason:{reason_code}')
    if task.get('attempts'):
        reasons.append(f"attempts:{task['attempts']}")
    return reasons


def playbook_aware_sort_key(task: Dict[str, Any], playbooks_dir: Optional[Path]):
    playbook_path = playbook_path_for(task.get('domain', ''), playbooks_dir)
    has_playbook = bool(playbook_path)
    base = candidate_priority_tuple(task)
    return (base[0], 0 if has_playbook else 1, base[1], base[2], base[3], base[4])


def render_candidate(task: Dict[str, Any], playbooks_dir: Optional[Path]) -> Dict[str, Any]:
    playbook_path = playbook_path_for(task.get('domain', ''), playbooks_dir)
    has_playbook = bool(playbook_path)
    return {
        'task_id': task.get('task_id', ''),
        'row_id': task.get('row_id', ''),
        'domain': task.get('domain', ''),
        'status': task.get('status', ''),
        'phase': task.get('phase', ''),
        'reason_code': task.get('reason_code', ''),
        'route': task.get('route', ''),
        'attempts': task.get('attempts', 0),
        'artifact_ref': task.get('artifact_ref', ''),
        'playbook_id': task.get('playbook_id', ''),
        'playbook_path': str(playbook_path) if playbook_path else '',
        'selection_score': list(candidate_priority_tuple(task)),
        'estimated_friction': estimated_friction(task),
        'submit_likelihood': submit_likelihood(task, has_playbook),
        'why_selected': selection_reasons(task, has_playbook),
        'updated_at': task.get('updated_at', ''),
        'locked': bool(task.get('locked_by')),
    }


def compact_event(event: Dict[str, Any]) -> Dict[str, Any]:
    keys = ['ts', 'action', 'event', 'task_id', 'row_id', 'domain', 'status', 'phase', 'reason_code', 'message', 'note']
    return {key: event[key] for key in keys if key in event and event[key] not in ('', None)}


def main() -> int:
    parser = argparse.ArgumentParser(description='Generate a compact worker brief for Web Backlinker small-batch runs.')
    parser.add_argument('--store', required=True)
    parser.add_argument('--manifest', required=True)
    parser.add_argument('--events', required=True)
    parser.add_argument('--product-profile', required=True)
    parser.add_argument('--playbooks-dir', default='')
    parser.add_argument('--output', default='')
    parser.add_argument('--limit', type=int, default=3)
    parser.add_argument('--recent-events', type=int, default=5)
    args = parser.parse_args()

    store_path = Path(args.store).expanduser().resolve()
    manifest_path = Path(args.manifest).expanduser().resolve()
    events_path = Path(args.events).expanduser().resolve()
    product_profile_path = Path(args.product_profile).expanduser().resolve()
    playbooks_dir = Path(args.playbooks_dir).expanduser().resolve() if args.playbooks_dir else None
    output_path = Path(args.output).expanduser().resolve() if args.output else default_output_path(store_path)

    store = load_store(store_path)
    manifest = load_json(manifest_path)
    tasks = store['tasks']
    candidate_pool = next_candidates(tasks, limit=max(args.limit * 10, 12))
    candidates = sorted(candidate_pool, key=lambda task: playbook_aware_sort_key(task, playbooks_dir))[:args.limit]
    local_counts = {}
    for task in tasks:
        local_counts[task['status']] = local_counts.get(task['status'], 0) + 1
    lease_path = derive_lease_path(store_path)
    lease = load_lease(lease_path)

    brief = {
        'brief_version': 1,
        'generated_at': now_iso(),
        'run_id': manifest.get('run_id', ''),
        'manifest_path': str(manifest_path),
        'task_store_path': str(store_path),
        'events_path': str(events_path),
        'product_profile_path': str(product_profile_path),
        'lease_path': str(lease_path),
        'run_summary': {
            'state': manifest.get('state', ''),
            'sheet_url': manifest.get('sheet_url', ''),
            'promoted': manifest.get('promoted', ''),
            'updated_at': manifest.get('updated_at', ''),
            'summary': manifest.get('summary', ''),
            'last_row_id': manifest.get('last_processed_row_id') or manifest.get('last_row_id', ''),
            'last_domain': manifest.get('last_processed_domain') or manifest.get('last_domain', ''),
            'last_status': manifest.get('last_status', ''),
            'counts_local': local_counts,
            'counts_sheet': sheet_counts(tasks),
        },
        'lease': {
            'active': lease_is_active(lease),
            'owner_worker': lease.get('owner_worker', ''),
            'heartbeat_at': lease.get('heartbeat_at', ''),
            'expires_at': lease.get('expires_at', ''),
            'processed_count': lease.get('processed_count', 0),
            'last_task_id': lease.get('last_task_id', ''),
        },
        'candidates': [render_candidate(task, playbooks_dir) for task in candidates],
        'product_profile_min': minimal_product_profile(product_profile_path),
        'hard_rules': HARD_RULES,
        'recent_events': [compact_event(event) for event in tail_jsonl(events_path, args.recent_events)],
    }

    output_path.parent.mkdir(parents=True, exist_ok=True)
    output_path.write_text(json.dumps(brief, ensure_ascii=False, indent=2) + '\n', encoding='utf-8')
    print(json.dumps({'ok': True, 'output': str(output_path), 'candidate_count': len(brief['candidates'])}, ensure_ascii=False, indent=2))
    return 0


if __name__ == '__main__':
    raise SystemExit(main())
