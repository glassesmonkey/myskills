#!/usr/bin/env python3
from __future__ import annotations

import argparse
import json
from pathlib import Path
from typing import Any
from urllib.parse import parse_qsl, urlencode, urlsplit, urlunsplit

from common import default_base_dir, domain_from_url, load_json, now_iso, normalize_promoted_url, save_json, unique_notes
from task_store import find_task, load_store


def load_intake(path: Path) -> dict[str, Any]:
    return load_json(path, {}) if path.exists() else {}


def build_tracked_url(base_url: str, source: str, medium: str, campaign: str) -> str:
    parts = urlsplit(base_url)
    query = dict(parse_qsl(parts.query, keep_blank_values=True))
    query.update(
        {
            "utm_source": source,
            "utm_medium": medium,
            "utm_campaign": campaign,
        }
    )
    return urlunsplit((parts.scheme, parts.netloc, parts.path, urlencode(query, doseq=True), parts.fragment))


def load_account(path: Path, domain: str) -> dict[str, Any]:
    registry = load_json(path, {"records": []})
    records = registry.get("records", registry if isinstance(registry, list) else [])
    for record in records:
        if str(record.get("domain", "")).strip().lower() == domain:
            return record
    return {}


def load_playbook(path: Path, domain: str) -> dict[str, Any]:
    candidates = [domain]
    if domain.startswith("www."):
        candidates.append(domain[4:])
    else:
        candidates.append(f"www.{domain}")
    for candidate in candidates:
        if not candidate:
            continue
        playbook_path = path / "sites" / f"{candidate}.json"
        if playbook_path.exists():
            return load_json(playbook_path, {})
    return {}


def main() -> int:
    parser = argparse.ArgumentParser(description="Build a compact worker brief for one backlink task.")
    parser.add_argument("--store", required=True)
    parser.add_argument("--task-id", required=True)
    parser.add_argument("--profile", required=True)
    parser.add_argument("--base-dir", default=str(default_base_dir()))
    parser.add_argument("--playbooks-dir", default="")
    parser.add_argument("--accounts", default="")
    parser.add_argument("--utm-medium", default="directory")
    parser.add_argument("--utm-campaign", default="backlink")
    parser.add_argument("--out", default="")
    args = parser.parse_args()

    store_path = Path(args.store).expanduser().resolve()
    profile_path = Path(args.profile).expanduser().resolve()
    base_dir = Path(args.base_dir).expanduser().resolve()
    playbooks_dir = Path(args.playbooks_dir).expanduser().resolve() if args.playbooks_dir else base_dir / "playbooks"
    accounts_path = Path(args.accounts).expanduser().resolve() if args.accounts else base_dir / "accounts" / "site-accounts.json"

    store = load_store(store_path)
    task = find_task(store, args.task_id)
    profile = load_json(profile_path, {})
    intake_path = profile_path.with_suffix(".intake.json")
    intake = load_intake(intake_path)
    domain = task.get("domain") or domain_from_url(task.get("normalized_url", ""))
    playbook = load_playbook(playbooks_dir, domain)
    account = load_account(accounts_path, domain)

    canonical_url = normalize_promoted_url(profile.get("canonical_url") or profile.get("promoted_url") or store.get("promoted_url", ""))
    tracked_url = build_tracked_url(canonical_url, domain or "target", args.utm_medium, args.utm_campaign)
    contact_emails = profile.get("facts", {}).get("contact_emails", []) or []
    missing_fields = unique_notes(
        [
            *(profile.get("missing_fields", []) or []),
            "company_email" if not contact_emails else "",
        ],
        limit=20,
    )

    brief = {
        "generated_at": now_iso(),
        "task": {
            "task_id": task.get("task_id", ""),
            "domain": domain,
            "target_url": task.get("normalized_url", ""),
            "status": task.get("status", ""),
            "site_type": task.get("site_type", "unknown"),
            "auth_type": task.get("auth_type", "unknown"),
            "oauth_providers": task.get("oauth_providers", []) or [],
            "anti_bot": task.get("anti_bot", "unknown"),
            "captcha_tier": task.get("captcha_tier", "unknown"),
            "blocker_type": task.get("blocker_type", ""),
            "requires_reciprocal_backlink": task.get("requires_reciprocal_backlink", False),
            "route": task.get("route", ""),
            "execution_mode": task.get("execution_mode", ""),
        },
        "promoted_site": {
            "product_name": profile.get("product_name", ""),
            "canonical_url": canonical_url,
            "tracked_url": tracked_url,
            "one_liner": profile.get("one_liner", ""),
            "short_description": profile.get("short_description", ""),
            "medium_description": profile.get("medium_description", ""),
            "contact_emails": contact_emails[:3],
            "submitter_name": intake.get("submitter_name", ""),
            "preferred_verification_email": intake.get("preferred_verification_email", ""),
            "feature_hints": (profile.get("materials", {}) or {}).get("feature_hints", [])[:6],
        },
        "playbook": {
            "matched": bool(playbook),
            "playbook_id": playbook.get("playbook_id", ""),
            "entrypoints": playbook.get("entrypoints", {}),
            "field_map": playbook.get("field_map", {}),
            "replay_confidence": playbook.get("replay_confidence", 0.0),
            "stability_score": playbook.get("stability_score", 0.0),
        },
        "account": {
            "matched": bool(account),
            "account_ref": account.get("account_ref", ""),
            "auth_type": account.get("auth_type", ""),
            "signup_email": account.get("signup_email", ""),
            "browser_profile_ref": account.get("browser_profile_ref", ""),
            "status": account.get("status", ""),
        },
        "policy": {
            "allow_oauth_login": bool(intake.get("allow_oauth_login", False)),
            "allow_gmail_signup": bool(intake.get("allow_gmail_signup", False)),
            "allow_manual_captcha": bool(intake.get("allow_manual_captcha", False)),
            "allow_paid_listing": bool(intake.get("allow_paid_listing", False)),
            "allow_reciprocal_backlink": bool(intake.get("allow_reciprocal_backlink", False)),
            "allow_phone_disclosure": bool(intake.get("allow_phone_disclosure", False)),
            "allow_address_disclosure": bool(intake.get("allow_address_disclosure", False)),
        },
        "missing_fields": missing_fields,
        "next_focus": unique_notes(
            [
                "reuse matched playbook" if playbook else "",
                "reuse matched account" if account else "",
                "be ready for mailbox verification" if task.get("auth_type") in {"email_signup", "magic_link"} else "",
                "decide whether to accept reciprocal backlink requirement" if task.get("requires_reciprocal_backlink") else "",
                "park the row immediately on managed anti-bot" if task.get("anti_bot") not in {"", "none", "unknown"} else "",
            ],
            limit=10,
        ),
    }

    if args.out:
        out_path = Path(args.out).expanduser().resolve()
        save_json(out_path, brief)
        print(json.dumps({"ok": True, "brief_path": str(out_path), "brief": brief}, ensure_ascii=False, indent=2))
        return 0

    print(json.dumps({"ok": True, "brief": brief}, ensure_ascii=False, indent=2))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
