#!/usr/bin/env python3
from __future__ import annotations

import argparse
import json
from pathlib import Path
from typing import Any

from common import default_base_dir, domain_from_url, load_json, now_iso, save_json, unique_notes


def load_scout(path: Path) -> dict[str, Any]:
    return load_json(path, {})


def default_playbooks_dir() -> Path:
    return default_base_dir() / "playbooks"


def automation_from_scout(scout: dict[str, Any]) -> str:
    if scout.get("anti_bot") not in {"", "none"}:
        return "DEFER_RETRY"
    if scout.get("site_type") in {"directory", "launch_platform"} and scout.get("auth_type") in {"none", "email_signup"}:
        return "AUTO_EXECUTE"
    return "ASSISTED_EXECUTE"


def confidence_from_scout(scout: dict[str, Any]) -> float:
    if scout.get("anti_bot") not in {"", "none"}:
        return 0.1
    if scout.get("forms") and scout.get("field_map"):
        return 0.45
    if scout.get("candidate_submit_url"):
        return 0.30
    return 0.15


def build_playbook(scout: dict[str, Any], account_ref: str, mailbox_account: str) -> dict[str, Any]:
    domain = scout.get("domain") or domain_from_url(scout.get("target_url", ""))
    if domain.startswith("www."):
        domain = domain[4:]
    candidate_submit_url = scout.get("candidate_submit_url", "") or scout.get("target_url", "")
    notes = list(scout.get("notes", []) or [])
    if scout.get("forms"):
        notes.append(f"scaffolded from {len(scout['forms'])} observed forms")
    if scout.get("field_map"):
        notes.append("field map guessed from scouting")

    return {
        "playbook_id": f"site-{domain}",
        "scope": "site",
        "domain_or_family": domain,
        "domain": domain,
        "site_type": scout.get("site_type", "unknown"),
        "auth_type": scout.get("auth_type", "unknown"),
        "submission_type": "form" if scout.get("forms") else "unknown",
        "entrypoints": {
            "home": scout.get("target_url", ""),
            "submit": candidate_submit_url,
        },
        "field_map": scout.get("field_map", {}),
        "steps": [
            {
                "step_index": 1,
                "action": "open",
                "target": candidate_submit_url,
                "goal": "reach the submit surface discovered by scouting",
            }
        ],
        "success_signals": ["thank you", "submitted", "pending review", "check your email"],
        "failure_signals": unique_notes(
            [
                scout.get("anti_bot", "") if scout.get("anti_bot") not in {"", "none"} else "",
                scout.get("captcha_tier", "") if scout.get("captcha_tier") not in {"", "none"} else "",
            ],
            limit=6,
        ),
        "result_checks": {
            "url_changed": True,
            "success_text_any": ["thank you", "submitted", "pending review", "check your email"],
        },
        "simple_captcha_supported": "allowed" if str(scout.get("captcha_tier", "")).startswith("simple_") else "unknown",
        "anti_bot_policy": "park_on_managed",
        "execution_mode": "session_browser",
        "automation_disposition": automation_from_scout(scout),
        "account_ref": account_ref,
        "credential_ref": "",
        "browser_profile_ref": "",
        "mailbox_account": mailbox_account,
        "success_count": 0,
        "stability_score": confidence_from_scout(scout),
        "replay_confidence": confidence_from_scout(scout),
        "last_success_at": "",
        "updated_at": now_iso(),
        "notes": unique_notes(notes, limit=20),
    }


def main() -> int:
    parser = argparse.ArgumentParser(description="Create a first-pass site playbook from a scout artifact.")
    parser.add_argument("--scout-file", required=True)
    parser.add_argument("--playbooks-dir", default=str(default_playbooks_dir()))
    parser.add_argument("--account-ref", default="")
    parser.add_argument("--mailbox-account", default="")
    parser.add_argument("--out", default="")
    args = parser.parse_args()

    scout = load_scout(Path(args.scout_file).expanduser().resolve())
    if not scout.get("domain") and not scout.get("target_url"):
        raise SystemExit("scout file is empty or missing domain/target_url")
    playbook = build_playbook(scout, args.account_ref, args.mailbox_account)
    playbooks_dir = Path(args.playbooks_dir).expanduser().resolve()
    out_path = Path(args.out).expanduser().resolve() if args.out else playbooks_dir / "sites" / f"{playbook['domain']}.json"

    current = load_json(out_path, {}) if out_path.exists() else {}
    merged = {**current, **playbook}
    merged["notes"] = unique_notes([*(current.get("notes", []) or []), *(playbook.get("notes", []) or [])], limit=20)
    merged["updated_at"] = now_iso()
    save_json(out_path, merged)
    print(json.dumps({"ok": True, "playbook_path": str(out_path), "playbook": merged}, ensure_ascii=False, indent=2))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
