#!/usr/bin/env python3
import argparse
import json
import os
from copy import deepcopy
from datetime import datetime, timezone
from pathlib import Path
from typing import Any, Dict, Optional

import yaml

SCRIPT_DIR = Path(__file__).resolve().parent
if str(SCRIPT_DIR) not in os.sys.path:
    os.sys.path.insert(0, str(SCRIPT_DIR))

from task_store import append_event, find_task, load_store, now_iso, save_store  # noqa: E402


HARD_REJECT_REASONS = {
    'payment_required',
    'phone_verification',
    'suspicious_site',
    'oauth_scope_review',
}
ASSIST_REASONS = {
    'captcha',
    'captcha_required',
    'cloudflare_challenge',
    'manual_content_needed',
}
REVIEW_LATER_REASONS = {
    'backlink_required',
}
DEFER_REASONS = {
    'missing_config',
    'site_error',
}


def load_json(path: Path):
    return json.loads(path.read_text(encoding='utf-8'))


def load_yaml(path: Path):
    return yaml.safe_load(path.read_text(encoding='utf-8')) or {}


def load_account_registry(path: Path) -> Dict[str, Any]:
    if not path.exists():
        return {'updated_at': '', 'records': []}
    raw = load_json(path)
    if isinstance(raw, list):
        raw = {'updated_at': '', 'records': raw}
    raw.setdefault('records', [])
    return raw


def find_playbook(domain: str, playbooks_dir: Optional[Path]) -> Optional[Path]:
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


def find_account(domain: str, registry: Dict[str, Any]) -> Optional[Dict[str, Any]]:
    key = (domain or '').strip().lower()
    for record in registry.get('records', []):
        if str(record.get('domain', '')).strip().lower() == key:
            return record
    return None


def confidence_from_playbook(playbook: Dict[str, Any]) -> float:
    replay = float(playbook.get('replay_confidence', 0.0) or 0.0)
    stability = float(playbook.get('stability_score', 0.0) or 0.0)
    return max(replay, stability)


def choose_plan(task: Dict[str, Any], playbook: Optional[Dict[str, Any]], account: Optional[Dict[str, Any]],
                min_direct_conf: float, min_observe_conf: float) -> Dict[str, Any]:
    domain = task.get('domain', '')
    site_type = task.get('site_type', 'unknown') or 'unknown'
    auth_type = task.get('auth_type', 'unknown') or 'unknown'
    reason = (task.get('reason_code') or '').strip().lower()
    plan = {
        'route': task.get('route', '') or 'skip',
        'execution_mode': task.get('execution_mode', '') or 'manual',
        'automation_disposition': task.get('automation_disposition', '') or 'ASSISTED_EXECUTE',
        'playbook_id': task.get('playbook_id', ''),
        'playbook_confidence': float(task.get('playbook_confidence', 0.0) or 0.0),
        'replay_status': task.get('replay_status', '') or 'not_compiled',
        'account_ref': task.get('account_ref', ''),
        'credential_ref': task.get('credential_ref', ''),
        'last_validated_at': task.get('last_validated_at', ''),
        'rationale': [],
        'next_action': '',
    }

    if playbook:
        plan['playbook_id'] = playbook.get('playbook_id', '')
        plan['playbook_confidence'] = confidence_from_playbook(playbook)
        plan['replay_status'] = 'validated' if plan['playbook_confidence'] >= min_direct_conf else 'compiled'
        plan['last_validated_at'] = playbook.get('last_validated_at', '') or task.get('last_validated_at', '')
        plan['account_ref'] = playbook.get('account_ref') or plan['account_ref']
        plan['credential_ref'] = playbook.get('credential_ref') or plan['credential_ref']
        plan['rationale'].append('matched_site_playbook')

    if account:
        plan['account_ref'] = account.get('account_ref', '') or plan['account_ref']
        plan['credential_ref'] = account.get('credential_ref', '') or plan['credential_ref']
        plan['rationale'].append('matched_account_registry')

    if reason in HARD_REJECT_REASONS:
        plan.update({
            'route': 'skip',
            'execution_mode': 'manual',
            'automation_disposition': 'REJECT',
            'next_action': f'reject:{reason}',
        })
        plan['rationale'].append(f'hard_reject_reason:{reason}')
        return plan

    if reason in ASSIST_REASONS:
        plan.update({
            'route': task.get('route', '') or 'needs_human',
            'execution_mode': 'manual',
            'automation_disposition': 'ASSISTED_EXECUTE',
            'next_action': f'assist_or_park:{reason}',
        })
        plan['rationale'].append(f'assist_reason:{reason}')
        return plan

    if reason in REVIEW_LATER_REASONS:
        plan.update({
            'route': 'dir_reciprocal_review',
            'execution_mode': 'manual',
            'automation_disposition': 'ASSISTED_EXECUTE',
            'next_action': 'record_for_manual_link_exchange_review',
        })
        plan['rationale'].append(f'review_later_reason:{reason}')
        return plan

    if reason in DEFER_REASONS:
        plan.update({
            'route': task.get('route', '') or 'skip',
            'execution_mode': 'manual',
            'automation_disposition': 'DEFER_RETRY',
            'next_action': f'defer:{reason}',
        })
        plan['rationale'].append(f'defer_reason:{reason}')
        return plan

    if site_type in {'community', 'forum'}:
        plan.update({
            'route': 'community_post_needed',
            'execution_mode': 'manual',
            'automation_disposition': 'ASSISTED_EXECUTE',
            'next_action': 'manual_content_review',
        })
        plan['rationale'].append('community_surface_outside_fast_path')
        return plan

    if site_type == 'article_platform':
        plan.update({
            'route': 'article_pitch_needed',
            'execution_mode': 'manual',
            'automation_disposition': 'REJECT',
            'next_action': 'out_of_v1_scope',
        })
        plan['rationale'].append('article_platform_out_of_scope')
        return plan

    if playbook and playbook.get('execution_mode') == 'browser_use_direct':
        pb_auto = playbook.get('automation_disposition', 'ASSISTED_EXECUTE')
        if plan['playbook_confidence'] >= min_direct_conf and pb_auto == 'AUTO_EXECUTE':
            plan.update({
                'route': task.get('route', '') or ('dir_email_signup' if auth_type == 'email_signup' else 'dir_noauth_submit'),
                'execution_mode': 'browser_use_direct',
                'automation_disposition': 'AUTO_EXECUTE',
                'replay_status': 'validated',
                'next_action': 'run_compiled_playbook',
            })
            plan['rationale'].append('validated_fast_path_playbook')
            return plan
        if plan['playbook_confidence'] >= min_observe_conf:
            plan.update({
                'route': task.get('route', '') or ('dir_email_signup' if auth_type == 'email_signup' else 'dir_noauth_submit'),
                'execution_mode': 'browser_use_direct_observe',
                'automation_disposition': 'ASSISTED_EXECUTE',
                'replay_status': 'observe',
                'next_action': 'replay_with_observation',
            })
            plan['rationale'].append('compiled_playbook_needs_replay_validation')
            return plan

    if auth_type == 'google_oauth':
        plan.update({
            'route': 'dir_google_oauth',
            'execution_mode': 'relay_auth',
            'automation_disposition': 'ASSISTED_EXECUTE',
            'next_action': 'relay_or_profile_auth',
        })
        plan['rationale'].append('google_oauth_prefers_relay')
        return plan

    if auth_type == 'magic_link':
        plan.update({
            'route': 'dir_email_signup',
            'execution_mode': 'native_submit',
            'automation_disposition': 'ASSISTED_EXECUTE',
            'next_action': 'email_link_flow',
        })
        plan['rationale'].append('magic_link_requires_followup')
        return plan

    if auth_type == 'email_signup':
        plan.update({
            'route': 'dir_email_signup',
            'execution_mode': 'native_submit',
            'automation_disposition': 'AUTO_EXECUTE' if site_type in {'directory', 'launch_platform', 'unknown'} else 'ASSISTED_EXECUTE',
            'next_action': 'reuse_account' if account else 'register_or_reuse_account',
        })
        if account:
            plan['rationale'].append('reusable_email_signup_account_available')
        else:
            plan['rationale'].append('email_signup_preferred_over_oauth')
        return plan

    if auth_type in {'none', 'unknown'}:
        plan.update({
            'route': 'dir_noauth_submit',
            'execution_mode': 'native_submit',
            'automation_disposition': 'AUTO_EXECUTE',
            'next_action': 'submit_directly' if domain else 'scout_submit_surface',
        })
        plan['rationale'].append('noauth_or_unknown_defaults_to_native_scout_submit')
        return plan

    plan['rationale'].append('fallback_manual_default')
    plan['next_action'] = 'manual_review'
    return plan


def apply_plan(store_path: Path, events_path: Optional[Path], task_id: str, plan: Dict[str, Any],
               site_type: str, auth_type: str, submission_type: str) -> Dict[str, Any]:
    data = load_store(store_path)
    task = find_task(data, task_id)
    task['route'] = plan['route']
    task['execution_mode'] = plan['execution_mode']
    task['automation_disposition'] = plan['automation_disposition']
    task['playbook_id'] = plan['playbook_id']
    task['playbook_confidence'] = plan['playbook_confidence']
    task['replay_status'] = plan['replay_status']
    task['account_ref'] = plan['account_ref']
    task['credential_ref'] = plan['credential_ref']
    task['last_validated_at'] = plan['last_validated_at']
    task['site_type'] = site_type
    task['auth_type'] = auth_type
    task['submission_type'] = submission_type
    task['updated_at'] = now_iso()
    save_store(store_path, data)
    if events_path:
        append_event(events_path, {
            'ts': now_iso(),
            'action': 'select_execution_plan',
            'task_id': task['task_id'],
            'row_id': task.get('row_id', ''),
            'domain': task.get('domain', ''),
            'site_type': site_type,
            'auth_type': auth_type,
            'submission_type': submission_type,
            'route': plan['route'],
            'execution_mode': plan['execution_mode'],
            'automation_disposition': plan['automation_disposition'],
            'playbook_id': plan['playbook_id'],
            'account_ref': plan['account_ref'],
            'note': '; '.join(plan['rationale']),
        })
    return task


def main() -> int:
    parser = argparse.ArgumentParser(description='Select execution route/mode for a Web Backlinker task.')
    parser.add_argument('--task-store', default='')
    parser.add_argument('--task', default='')
    parser.add_argument('--task-json', default='')
    parser.add_argument('--events', default='')
    parser.add_argument('--playbooks-dir', default='')
    parser.add_argument('--account-registry', default='')
    parser.add_argument('--site-type', default='')
    parser.add_argument('--auth-type', default='')
    parser.add_argument('--submission-type', default='')
    parser.add_argument('--min-direct-confidence', type=float, default=0.85)
    parser.add_argument('--min-observe-confidence', type=float, default=0.60)
    parser.add_argument('--apply', action='store_true')
    args = parser.parse_args()

    if not args.task_json and not (args.task_store and args.task):
        raise SystemExit('provide either --task-json or both --task-store and --task')

    task: Dict[str, Any]
    store_path: Optional[Path] = None
    if args.task_json:
        task = load_json(Path(args.task_json).expanduser().resolve())
    else:
        store_path = Path(args.task_store).expanduser().resolve()
        data = load_store(store_path)
        task = deepcopy(find_task(data, args.task))

    site_type = args.site_type or task.get('site_type', 'unknown') or 'unknown'
    auth_type = args.auth_type or task.get('auth_type', 'unknown') or 'unknown'
    submission_type = args.submission_type or task.get('submission_type', 'unknown') or 'unknown'
    task['site_type'] = site_type
    task['auth_type'] = auth_type
    task['submission_type'] = submission_type

    playbooks_dir = Path(args.playbooks_dir).expanduser().resolve() if args.playbooks_dir else None
    registry_path = Path(args.account_registry).expanduser().resolve() if args.account_registry else None
    playbook_path = find_playbook(task.get('domain', ''), playbooks_dir)
    playbook = load_yaml(playbook_path) if playbook_path else None
    registry = load_account_registry(registry_path) if registry_path else {'records': []}
    account = find_account(task.get('domain', ''), registry)

    plan = choose_plan(task, playbook, account, args.min_direct_confidence, args.min_observe_confidence)
    payload = {
        'ok': True,
        'task_id': task.get('task_id', ''),
        'domain': task.get('domain', ''),
        'site_type': site_type,
        'auth_type': auth_type,
        'submission_type': submission_type,
        'playbook_path': str(playbook_path) if playbook_path else '',
        'account_registry_match': account.get('account_ref', '') if account else '',
        'plan': plan,
    }

    if args.apply:
        if not store_path:
            raise SystemExit('--apply requires --task-store and --task')
        task = apply_plan(store_path, Path(args.events).expanduser().resolve() if args.events else None, args.task, plan, site_type, auth_type, submission_type)
        payload['applied_task'] = task

    print(json.dumps(payload, ensure_ascii=False, indent=2))
    return 0


if __name__ == '__main__':
    raise SystemExit(main())
