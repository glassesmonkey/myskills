#!/usr/bin/env python3
import argparse
import json
import os
import subprocess
from pathlib import Path
from typing import Any, Dict, List

import yaml

SCRIPT_DIR = Path(__file__).resolve().parent
SAFE_BIN = SCRIPT_DIR / 'browser_use_safe.sh'


def load_yaml(path: Path) -> Dict[str, Any]:
    return yaml.safe_load(path.read_text(encoding='utf-8')) or {}


def load_json(path: Path) -> Dict[str, Any]:
    return json.loads(path.read_text(encoding='utf-8'))


def resolve_value(step: Dict[str, Any], profile: Dict[str, Any]) -> str:
    if step.get('value') not in (None, ''):
        return str(step['value'])
    source = str(step.get('input_source', '')).strip()
    if not source:
        return ''
    if source.startswith('profile:'):
        key = source.split(':', 1)[1]
        value = profile.get(key, '')
        if isinstance(value, (list, dict)):
            return json.dumps(value, ensure_ascii=False)
        return str(value)
    if source.startswith('literal:'):
        return source.split(':', 1)[1]
    return source


def run_safe(args: List[str], env: Dict[str, str]) -> subprocess.CompletedProcess:
    return subprocess.run([str(SAFE_BIN), *args], capture_output=True, text=True, env=env)


def step_to_command(step: Dict[str, Any], profile: Dict[str, Any]) -> List[str]:
    action = step.get('action_type')
    if action == 'open':
        return ['open', step.get('url') or resolve_value(step, profile)]
    if action == 'click':
        return ['click', str(step['target'])]
    if action == 'input':
        return ['input', str(step['target']), resolve_value(step, profile)]
    if action == 'type':
        return ['type', resolve_value(step, profile)]
    if action == 'keys':
        return ['keys', resolve_value(step, profile)]
    if action == 'select':
        return ['select', str(step['target']), resolve_value(step, profile)]
    if action == 'wait_selector':
        cmd = ['wait', 'selector', step['selector']]
        if step.get('timeout_ms'):
            cmd.extend(['--timeout', str(step['timeout_ms'])])
        if step.get('state'):
            cmd.extend(['--state', str(step['state'])])
        return cmd
    if action == 'wait_text':
        cmd = ['wait', 'text', resolve_value(step, profile)]
        if step.get('timeout_ms'):
            cmd.extend(['--timeout', str(step['timeout_ms'])])
        return cmd
    if action == 'get_title':
        return ['get', 'title']
    if action == 'state':
        return ['state']
    if action == 'screenshot':
        cmd = ['screenshot']
        if step.get('path'):
            cmd.append(str(step['path']))
        if step.get('full'):
            cmd.append('--full')
        return cmd
    if action == 'close':
        return ['close']
    raise SystemExit(f'unsupported action_type: {action}')


def main() -> int:
    parser = argparse.ArgumentParser(description='Run a browser_use_direct site playbook against a promoted-site profile.')
    parser.add_argument('--playbook', required=True)
    parser.add_argument('--product-profile', required=True)
    parser.add_argument('--no-reset', action='store_true')
    args = parser.parse_args()

    playbook = load_yaml(Path(args.playbook).expanduser().resolve())
    profile = load_json(Path(args.product_profile).expanduser().resolve())
    if playbook.get('execution_mode') != 'browser_use_direct':
        raise SystemExit('playbook execution_mode must be browser_use_direct')

    steps = playbook.get('direct_steps') or []
    if not steps:
        raise SystemExit('playbook has no direct_steps')

    env = os.environ.copy()
    outputs = []
    if not args.no_reset:
        reset = run_safe(['reset'], env)
        outputs.append({'command': ['reset'], 'returncode': reset.returncode, 'stdout': reset.stdout, 'stderr': reset.stderr})
        if reset.returncode != 0:
            print(json.dumps({'ok': False, 'step_outputs': outputs}, ensure_ascii=False, indent=2))
            return reset.returncode

    for idx, step in enumerate(steps, start=1):
        command = step_to_command(step, profile)
        result = run_safe(command, env)
        outputs.append({
            'step_index': idx,
            'action_type': step.get('action_type'),
            'goal': step.get('goal', ''),
            'command': command,
            'returncode': result.returncode,
            'stdout': result.stdout,
            'stderr': result.stderr,
        })
        if result.returncode != 0:
            print(json.dumps({'ok': False, 'failed_step': idx, 'step_outputs': outputs}, ensure_ascii=False, indent=2))
            return result.returncode

    print(json.dumps({'ok': True, 'step_outputs': outputs, 'playbook_id': playbook.get('playbook_id', '')}, ensure_ascii=False, indent=2))
    return 0


if __name__ == '__main__':
    raise SystemExit(main())
