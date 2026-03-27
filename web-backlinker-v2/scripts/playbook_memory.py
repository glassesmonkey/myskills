#!/usr/bin/env python3
from __future__ import annotations

import argparse
import json
from pathlib import Path
from typing import Any

from common import default_base_dir, load_json, now_iso, save_json, slugify, unique_notes


def default_playbooks_dir() -> Path:
    return default_base_dir() / "playbooks"


def parse_json_arg(value: str, default: Any) -> Any:
    if not value:
        return default
    return json.loads(value)


def playbook_path(base_dir: Path, scope: str, name: str) -> Path:
    folder = "sites" if scope == "site" else "patterns"
    return base_dir / folder / f"{slugify(name)}.json"


def normalize_playbook(record: dict[str, Any]) -> dict[str, Any]:
    domain_or_family = str(record.get("domain_or_family", "")).strip().lower()
    scope = str(record.get("scope", "site")).strip() or "site"
    normalized = {
        "playbook_id": str(record.get("playbook_id", "")).strip() or f"{scope}-{slugify(domain_or_family or 'playbook')}",
        "scope": scope,
        "domain_or_family": domain_or_family,
        "domain": str(record.get("domain", "")).strip().lower() or (domain_or_family if scope == "site" else ""),
        "site_type": str(record.get("site_type", "unknown")).strip() or "unknown",
        "auth_type": str(record.get("auth_type", "unknown")).strip() or "unknown",
        "submission_type": str(record.get("submission_type", "unknown")).strip() or "unknown",
        "entrypoints": record.get("entrypoints", {}) or {},
        "field_map": record.get("field_map", {}) or {},
        "steps": record.get("steps", []) or [],
        "success_signals": record.get("success_signals", []) or [],
        "failure_signals": record.get("failure_signals", []) or [],
        "result_checks": record.get("result_checks", {}) or {},
        "simple_captcha_supported": str(record.get("simple_captcha_supported", "unknown")).strip() or "unknown",
        "anti_bot_policy": str(record.get("anti_bot_policy", "park_on_managed")).strip() or "park_on_managed",
        "execution_mode": str(record.get("execution_mode", "session_browser")).strip() or "session_browser",
        "automation_disposition": str(record.get("automation_disposition", "ASSISTED_EXECUTE")).strip() or "ASSISTED_EXECUTE",
        "account_ref": str(record.get("account_ref", "")).strip(),
        "credential_ref": str(record.get("credential_ref", "")).strip(),
        "browser_profile_ref": str(record.get("browser_profile_ref", "")).strip(),
        "mailbox_account": str(record.get("mailbox_account", "")).strip(),
        "success_count": int(record.get("success_count", 0) or 0),
        "stability_score": float(record.get("stability_score", 0.0) or 0.0),
        "replay_confidence": float(record.get("replay_confidence", 0.0) or 0.0),
        "last_success_at": str(record.get("last_success_at", "")).strip(),
        "updated_at": str(record.get("updated_at", "")).strip() or now_iso(),
        "notes": unique_notes(record.get("notes", [])),
    }
    return normalized


def load_playbook(path: Path) -> dict[str, Any]:
    return normalize_playbook(load_json(path, {})) if path.exists() else {}


def match_playbook(base_dir: Path, domain: str) -> tuple[dict[str, Any], Path | None]:
    base = domain.strip().lower()
    candidates = [base]
    if base.startswith("www."):
        candidates.append(base[4:])
    else:
        candidates.append(f"www.{base}")
    for candidate in candidates:
        path = playbook_path(base_dir, "site", candidate)
        if path.exists():
            return normalize_playbook(load_json(path, {})), path
    return {}, None


def main() -> int:
    parser = argparse.ArgumentParser(description="Manage reusable target-site playbooks.")
    parser.add_argument("--playbooks-dir", default=str(default_playbooks_dir()))
    sub = parser.add_subparsers(dest="command", required=True)

    upsert = sub.add_parser("upsert")
    upsert.add_argument("--scope", choices=["site", "pattern"], default="site")
    upsert.add_argument("--name", required=True)
    upsert.add_argument("--playbook-id", default="")
    upsert.add_argument("--site-type", default="unknown")
    upsert.add_argument("--auth-type", default="unknown")
    upsert.add_argument("--submission-type", default="unknown")
    upsert.add_argument("--entrypoints-json", default="{}")
    upsert.add_argument("--field-map-json", default="{}")
    upsert.add_argument("--steps-json", default="[]")
    upsert.add_argument("--success-signals-json", default="[]")
    upsert.add_argument("--failure-signals-json", default="[]")
    upsert.add_argument("--result-checks-json", default="{}")
    upsert.add_argument("--simple-captcha-supported", default="unknown")
    upsert.add_argument("--anti-bot-policy", default="park_on_managed")
    upsert.add_argument("--execution-mode", default="session_browser")
    upsert.add_argument("--automation-disposition", default="ASSISTED_EXECUTE")
    upsert.add_argument("--account-ref", default="")
    upsert.add_argument("--credential-ref", default="")
    upsert.add_argument("--browser-profile-ref", default="")
    upsert.add_argument("--mailbox-account", default="")
    upsert.add_argument("--success-count", type=int, default=0)
    upsert.add_argument("--stability-score", type=float, default=0.0)
    upsert.add_argument("--replay-confidence", type=float, default=0.0)
    upsert.add_argument("--last-success-at", default="")
    upsert.add_argument("--note", action="append", default=[])

    get = sub.add_parser("get")
    get.add_argument("--scope", choices=["site", "pattern"], default="site")
    get.add_argument("--name", required=True)

    match = sub.add_parser("match")
    match.add_argument("--domain", required=True)

    listing = sub.add_parser("list")
    listing.add_argument("--scope", choices=["site", "pattern"], default="site")

    record_success = sub.add_parser("record-success")
    record_success.add_argument("--domain", required=True)
    record_success.add_argument("--confidence-bump", type=float, default=0.1)
    record_success.add_argument("--stability-bump", type=float, default=0.1)
    record_success.add_argument("--note", action="append", default=[])

    args = parser.parse_args()
    base_dir = Path(args.playbooks_dir).expanduser().resolve()

    if args.command == "upsert":
        path = playbook_path(base_dir, args.scope, args.name)
        current = load_json(path, {})
        updated = normalize_playbook(
            {
                **current,
                "playbook_id": args.playbook_id or current.get("playbook_id", ""),
                "scope": args.scope,
                "domain_or_family": args.name,
                "domain": args.name if args.scope == "site" else current.get("domain", ""),
                "site_type": args.site_type or current.get("site_type", "unknown"),
                "auth_type": args.auth_type or current.get("auth_type", "unknown"),
                "submission_type": args.submission_type or current.get("submission_type", "unknown"),
                "entrypoints": parse_json_arg(args.entrypoints_json, current.get("entrypoints", {})),
                "field_map": parse_json_arg(args.field_map_json, current.get("field_map", {})),
                "steps": parse_json_arg(args.steps_json, current.get("steps", [])),
                "success_signals": parse_json_arg(args.success_signals_json, current.get("success_signals", [])),
                "failure_signals": parse_json_arg(args.failure_signals_json, current.get("failure_signals", [])),
                "result_checks": parse_json_arg(args.result_checks_json, current.get("result_checks", {})),
                "simple_captcha_supported": args.simple_captcha_supported,
                "anti_bot_policy": args.anti_bot_policy,
                "execution_mode": args.execution_mode,
                "automation_disposition": args.automation_disposition,
                "account_ref": args.account_ref or current.get("account_ref", ""),
                "credential_ref": args.credential_ref or current.get("credential_ref", ""),
                "browser_profile_ref": args.browser_profile_ref or current.get("browser_profile_ref", ""),
                "mailbox_account": args.mailbox_account or current.get("mailbox_account", ""),
                "success_count": args.success_count or current.get("success_count", 0),
                "stability_score": args.stability_score or current.get("stability_score", 0.0),
                "replay_confidence": args.replay_confidence or current.get("replay_confidence", 0.0),
                "last_success_at": args.last_success_at or current.get("last_success_at", ""),
                "notes": unique_notes([*(current.get("notes", []) or []), *args.note]),
                "updated_at": now_iso(),
            }
        )
        save_json(path, updated)
        print(json.dumps({"ok": True, "playbook_path": str(path), "playbook": updated}, ensure_ascii=False, indent=2))
        return 0

    if args.command == "get":
        path = playbook_path(base_dir, args.scope, args.name)
        if not path.exists():
            raise SystemExit(f"playbook not found: {path}")
        print(json.dumps({"ok": True, "playbook_path": str(path), "playbook": normalize_playbook(load_json(path, {}))}, ensure_ascii=False, indent=2))
        return 0

    if args.command == "match":
        playbook, path = match_playbook(base_dir, args.domain)
        print(json.dumps({"ok": bool(path), "playbook_path": str(path) if path else "", "playbook": playbook}, ensure_ascii=False, indent=2))
        return 0 if path else 1

    if args.command == "list":
        folder = base_dir / ("sites" if args.scope == "site" else "patterns")
        records = []
        for path in sorted(folder.glob("*.json")):
            records.append(normalize_playbook(load_json(path, {})))
        print(json.dumps({"ok": True, "count": len(records), "records": records}, ensure_ascii=False, indent=2))
        return 0

    playbook, path = match_playbook(base_dir, args.domain)
    if not path:
        raise SystemExit(f"site playbook not found for domain: {args.domain}")
    playbook["success_count"] = int(playbook.get("success_count", 0) or 0) + 1
    playbook["replay_confidence"] = min(1.0, float(playbook.get("replay_confidence", 0.0) or 0.0) + args.confidence_bump)
    playbook["stability_score"] = min(1.0, float(playbook.get("stability_score", 0.0) or 0.0) + args.stability_bump)
    playbook["last_success_at"] = now_iso()
    playbook["updated_at"] = now_iso()
    playbook["notes"] = unique_notes([*(playbook.get("notes", []) or []), *args.note])
    save_json(path, normalize_playbook(playbook))
    print(json.dumps({"ok": True, "playbook_path": str(path), "playbook": playbook}, ensure_ascii=False, indent=2))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
