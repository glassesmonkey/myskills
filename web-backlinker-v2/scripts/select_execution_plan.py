#!/usr/bin/env python3
from __future__ import annotations

import argparse
import json
from pathlib import Path
from typing import Any

from common import default_base_dir, domain_from_url, load_json, now_iso, save_json
from task_store import find_task, load_store, save_store


HARD_ANTI_BOT = {"cloudflare", "turnstile", "recaptcha", "hcaptcha", "managed"}
SIMPLE_CAPTCHA = {"simple_text", "simple_math", "simple_image"}


def load_account_registry(path: Path) -> dict[str, Any]:
    data = load_json(path, {"updated_at": "", "records": []})
    if isinstance(data, list):
        data = {"updated_at": "", "records": data}
    data.setdefault("records", [])
    return data


def find_account(path: Path, domain: str) -> dict[str, Any] | None:
    data = load_account_registry(path)
    key = domain.strip().lower()
    for record in data["records"]:
        if str(record.get("domain", "")).strip().lower() == key:
            return record
    return None


def find_playbook(playbooks_dir: Path, domain: str) -> tuple[dict[str, Any], Path | None]:
    base = domain.strip().lower()
    candidates = [base]
    if base.startswith("www."):
        candidates.append(base[4:])
    else:
        candidates.append(f"www.{base}")
    for candidate in candidates:
        path = playbooks_dir / "sites" / f"{candidate}.json"
        if path.exists():
            return load_json(path, {}), path
    return {}, None


def playbook_confidence(playbook: dict[str, Any]) -> float:
    return max(float(playbook.get("replay_confidence", 0.0) or 0.0), float(playbook.get("stability_score", 0.0) or 0.0))


def choose_plan(
    task: dict[str, Any],
    playbook: dict[str, Any],
    account: dict[str, Any] | None,
    intake: dict[str, Any] | None = None,
    min_direct: float = 0.85,
    min_observe: float = 0.60,
) -> dict[str, Any]:
    if intake is not None and not isinstance(intake, dict):
        legacy_min_direct = float(intake)
        legacy_min_observe = min_direct
        intake = {}
        min_direct = legacy_min_direct
        min_observe = legacy_min_observe
    intake = intake or {}
    route = "scout_more"
    execution_mode = "session_browser"
    automation_disposition = "ASSISTED_EXECUTE"
    next_action = "inspect_submit_surface"
    rationale: list[str] = []
    confidence = playbook_confidence(playbook) if playbook else 0.0

    anti_bot = str(task.get("anti_bot", "unknown")).strip().lower()
    captcha_tier = str(task.get("captcha_tier", "unknown")).strip().lower()
    auth_type = str(task.get("auth_type", "unknown")).strip().lower()
    oauth_providers = [str(item).strip().lower() for item in (task.get("oauth_providers", []) or []) if str(item).strip()]
    site_type = str(task.get("site_type", "unknown")).strip().lower()
    blocker_type = str(task.get("blocker_type", "")).strip().lower()
    requires_reciprocal_backlink = bool(task.get("requires_reciprocal_backlink", False)) or blocker_type == "reciprocal_backlink_required"
    oauth_allowed = bool(intake.get("allow_oauth_login", False))

    if anti_bot in HARD_ANTI_BOT:
        return {
            "route": "park_hard_antibot",
            "execution_mode": "manual",
            "automation_disposition": "AUTO_SKIP",
            "next_action": "skip_row",
            "playbook_id": playbook.get("playbook_id", "") if playbook else "",
            "playbook_confidence": confidence,
            "account_ref": account.get("account_ref", "") if account else "",
            "rationale": [f"hard_antibot:{anti_bot}"],
        }

    if requires_reciprocal_backlink:
        return {
            "route": "park_reciprocal_backlink",
            "execution_mode": "manual",
            "automation_disposition": "ASSISTED_EXECUTE",
            "next_action": "decide_reciprocal_backlink",
            "playbook_id": playbook.get("playbook_id", "") if playbook else "",
            "playbook_confidence": confidence,
            "account_ref": account.get("account_ref", "") if account else "",
            "rationale": ["reciprocal_backlink_required"],
        }

    if playbook and confidence >= min_direct and playbook.get("steps"):
        route = "replay_site_playbook"
        execution_mode = playbook.get("execution_mode", "session_browser")
        automation_disposition = "AUTO_EXECUTE"
        next_action = "run_playbook"
        rationale.append("validated_site_playbook")
    elif playbook and confidence >= min_observe and playbook.get("steps"):
        route = "observe_site_playbook"
        execution_mode = playbook.get("execution_mode", "session_browser")
        automation_disposition = "ASSISTED_EXECUTE"
        next_action = "run_playbook_with_observation"
        rationale.append("playbook_needs_more_validation")
    elif account and auth_type in {"email_signup", "magic_link"}:
        route = "reuse_email_account"
        execution_mode = "session_browser"
        automation_disposition = "AUTO_EXECUTE"
        next_action = "login_and_submit"
        rationale.append("reusable_email_account")
    elif auth_type == "none":
        route = "direct_submit"
        execution_mode = "session_browser"
        automation_disposition = "AUTO_EXECUTE"
        next_action = "submit_without_login"
        rationale.append("no_auth_route")
    elif auth_type == "email_signup":
        route = "register_email_account"
        execution_mode = "session_browser"
        automation_disposition = "AUTO_EXECUTE"
        next_action = "signup_then_watch_email"
        rationale.append("email_signup_preferred")
    elif auth_type in {"google_oauth", "facebook_oauth", "oauth"}:
        preferred_provider = "google" if "google" in oauth_providers or auth_type == "google_oauth" else "facebook" if "facebook" in oauth_providers or auth_type == "facebook_oauth" else "oauth"
        route = f"{preferred_provider}_oauth_login" if preferred_provider in {"google", "facebook"} else "oauth_login"
        execution_mode = "session_browser"
        automation_disposition = "AUTO_EXECUTE" if oauth_allowed else "ASSISTED_EXECUTE"
        next_action = "login_with_existing_shared_session" if oauth_allowed else "start_oauth_and_expect_human_credentials_if_needed"
        rationale.append("oauth_route")
        rationale.append(f"oauth_provider:{preferred_provider}")
        if not oauth_allowed:
            rationale.append("oauth_not_allowed_by_policy")
    elif auth_type == "magic_link":
        route = "magic_link_login"
        execution_mode = "session_browser"
        automation_disposition = "AUTO_EXECUTE"
        next_action = "request_magic_link_then_watch_email"
        rationale.append("magic_link_route")
    elif site_type in {"community", "forum", "article_platform"}:
        route = "park_for_manual_content"
        execution_mode = "manual"
        automation_disposition = "ASSISTED_EXECUTE"
        next_action = "park_row"
        rationale.append("content_surface_not_default_auto_path")
    else:
        rationale.append("insufficient_memory_or_classification")

    if captcha_tier in SIMPLE_CAPTCHA and anti_bot not in HARD_ANTI_BOT:
        rationale.append("attempt_simple_captcha_once")

    return {
        "route": route,
        "execution_mode": execution_mode,
        "automation_disposition": automation_disposition,
        "next_action": next_action,
        "playbook_id": playbook.get("playbook_id", "") if playbook else "",
        "playbook_confidence": confidence,
        "account_ref": (account or {}).get("account_ref", ""),
        "rationale": rationale,
    }


def main() -> int:
    parser = argparse.ArgumentParser(description="Choose the next execution route from task, playbook, and account memory.")
    parser.add_argument("--store", required=True)
    parser.add_argument("--task-id", required=True)
    parser.add_argument("--base-dir", default=str(default_base_dir()))
    parser.add_argument("--playbooks-dir", default="")
    parser.add_argument("--accounts", default="")
    parser.add_argument("--intake", default="")
    parser.add_argument("--min-direct-confidence", type=float, default=0.85)
    parser.add_argument("--min-observe-confidence", type=float, default=0.60)
    parser.add_argument("--apply", action="store_true")
    args = parser.parse_args()

    store_path = Path(args.store).expanduser().resolve()
    base_dir = Path(args.base_dir).expanduser().resolve()
    accounts_path = Path(args.accounts).expanduser().resolve() if args.accounts else base_dir / "accounts" / "site-accounts.json"
    playbooks_dir = Path(args.playbooks_dir).expanduser().resolve() if args.playbooks_dir else base_dir / "playbooks"
    intake_path = Path(args.intake).expanduser().resolve() if args.intake else Path("")

    store = load_store(store_path)
    task = find_task(store, args.task_id)
    domain = task.get("domain") or domain_from_url(task.get("normalized_url", ""))
    playbook, playbook_path = find_playbook(playbooks_dir, domain)
    account = find_account(accounts_path, domain)
    intake = load_json(intake_path, {}) if args.intake else {}
    plan = choose_plan(task, playbook, account, intake, args.min_direct_confidence, args.min_observe_confidence)
    plan["playbook_path"] = str(playbook_path) if playbook_path else ""

    if args.apply:
        task["route"] = plan["route"]
        task["execution_mode"] = plan["execution_mode"]
        task["automation_disposition"] = plan["automation_disposition"]
        task["playbook_id"] = plan["playbook_id"]
        task["playbook_confidence"] = plan["playbook_confidence"]
        task["account_ref"] = plan["account_ref"]
        task["updated_at"] = now_iso()
        save_store(store_path, store)

    print(json.dumps({"ok": True, "task_id": args.task_id, "plan": plan}, ensure_ascii=False, indent=2))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
