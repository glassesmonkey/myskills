#!/usr/bin/env python3
import argparse
import json
from pathlib import Path
from typing import Any, Dict, List

import yaml


REQUIRED_TOP_LEVEL = [
    'playbook_id',
    'scope',
    'site_type',
    'auth_type',
    'submission_type',
    'execution_mode',
    'automation_disposition',
    'entrypoints',
    'fallback_route',
]


def load_yaml(path: Path) -> Dict[str, Any]:
    return yaml.safe_load(path.read_text(encoding='utf-8')) or {}


def validate_direct_steps(steps: List[Dict[str, Any]]) -> List[str]:
    errors: List[str] = []
    if not steps:
        errors.append('direct_steps must be non-empty for browser_use_direct playbooks')
        return errors
    for idx, step in enumerate(steps, start=1):
        if not isinstance(step, dict):
            errors.append(f'direct_steps[{idx}] must be an object')
            continue
        if not step.get('action_type'):
            errors.append(f'direct_steps[{idx}].action_type is required')
    return errors


def main() -> int:
    parser = argparse.ArgumentParser(description='Validate a Web Backlinker site playbook.')
    parser.add_argument('--playbook', required=True)
    args = parser.parse_args()

    path = Path(args.playbook).expanduser().resolve()
    data = load_yaml(path)
    errors: List[str] = []
    warnings: List[str] = []

    for key in REQUIRED_TOP_LEVEL:
        if key not in data:
            errors.append(f'missing required field: {key}')

    entrypoints = data.get('entrypoints') or {}
    if not isinstance(entrypoints, dict):
        errors.append('entrypoints must be a mapping')

    execution_mode = data.get('execution_mode', 'native')
    if execution_mode == 'browser_use_direct':
        errors.extend(validate_direct_steps(data.get('direct_steps') or []))
        if not entrypoints.get('submit') and not entrypoints.get('home'):
            errors.append('browser_use_direct playbooks should define entrypoints.home or entrypoints.submit')
        if not data.get('result_checks'):
            warnings.append('browser_use_direct playbook has no result_checks; success detection may be weak')

    if data.get('automation_disposition') == 'AUTO_EXECUTE' and execution_mode != 'browser_use_direct':
        warnings.append('AUTO_EXECUTE without browser_use_direct is unusual; confirm this is intentional')

    print(json.dumps({
        'ok': not errors,
        'playbook': str(path),
        'errors': errors,
        'warnings': warnings,
        'execution_mode': execution_mode,
    }, ensure_ascii=False, indent=2))
    return 1 if errors else 0


if __name__ == '__main__':
    raise SystemExit(main())
