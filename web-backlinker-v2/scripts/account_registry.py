#!/usr/bin/env python3
from __future__ import annotations

import argparse
import json
from pathlib import Path
from typing import Any

from common import default_base_dir, now_iso, save_json, load_json, unique_notes


def default_registry_path() -> Path:
    return default_base_dir() / "accounts" / "site-accounts.json"


def normalize_record(record: dict[str, Any]) -> dict[str, Any]:
    domain = str(record.get("domain", "")).strip().lower()
    normalized = {
        "domain": domain,
        "account_ref": str(record.get("account_ref", "")).strip() or f"acct-{domain.replace('.', '-') or 'unknown'}",
        "auth_type": str(record.get("auth_type", "unknown")).strip() or "unknown",
        "signup_email": str(record.get("signup_email", "")).strip(),
        "username": str(record.get("username", "")).strip(),
        "credential_ref": str(record.get("credential_ref", "")).strip(),
        "browser_profile_ref": str(record.get("browser_profile_ref", "")).strip(),
        "mailbox_account": str(record.get("mailbox_account", "")).strip(),
        "oauth_provider": str(record.get("oauth_provider", "")).strip(),
        "created_at": str(record.get("created_at", "")).strip() or now_iso(),
        "last_verified_at": str(record.get("last_verified_at", "")).strip(),
        "status": str(record.get("status", "active")).strip() or "active",
        "notes": unique_notes(record.get("notes", [])),
    }
    return normalized


def load_registry(path: Path) -> dict[str, Any]:
    data = load_json(path, {"updated_at": "", "records": []})
    if isinstance(data, list):
        data = {"updated_at": "", "records": data}
    data.setdefault("updated_at", "")
    data.setdefault("records", [])
    return data


def save_registry(path: Path, data: dict[str, Any]) -> None:
    save_json(path, data)


def upsert_record(data: dict[str, Any], record: dict[str, Any]) -> dict[str, Any]:
    normalized = normalize_record(record)
    for index, existing in enumerate(data["records"]):
        if existing.get("domain") == normalized["domain"]:
            merged = normalize_record({**existing, **normalized})
            data["records"][index] = merged
            data["updated_at"] = now_iso()
            return merged
    data["records"].append(normalized)
    data["records"] = sorted((normalize_record(item) for item in data["records"]), key=lambda item: item["domain"])
    data["updated_at"] = now_iso()
    return normalized


def get_record(data: dict[str, Any], domain: str) -> dict[str, Any]:
    key = domain.strip().lower()
    for record in data["records"]:
        if record.get("domain") == key:
            return normalize_record(record)
    raise SystemExit(f"account not found for domain: {domain}")


def main() -> int:
    parser = argparse.ArgumentParser(description="Manage reusable per-domain account memory for backlink submissions.")
    parser.add_argument("--registry", default=str(default_registry_path()))
    sub = parser.add_subparsers(dest="command", required=True)

    upsert = sub.add_parser("upsert")
    upsert.add_argument("--domain", required=True)
    upsert.add_argument("--account-ref", default="")
    upsert.add_argument("--auth-type", default="unknown")
    upsert.add_argument("--signup-email", default="")
    upsert.add_argument("--username", default="")
    upsert.add_argument("--credential-ref", default="")
    upsert.add_argument("--browser-profile-ref", default="")
    upsert.add_argument("--mailbox-account", default="")
    upsert.add_argument("--oauth-provider", default="")
    upsert.add_argument("--created-at", default="")
    upsert.add_argument("--last-verified-at", default="")
    upsert.add_argument("--status", default="active")
    upsert.add_argument("--note", action="append", default=[])

    get = sub.add_parser("get")
    get.add_argument("--domain", required=True)

    listing = sub.add_parser("list")
    listing.add_argument("--auth-type", default="")
    listing.add_argument("--status", default="")

    touch = sub.add_parser("touch-verified")
    touch.add_argument("--domain", required=True)
    touch.add_argument("--status", default="")
    touch.add_argument("--at", default="")

    args = parser.parse_args()
    registry_path = Path(args.registry).expanduser().resolve()
    data = load_registry(registry_path)

    if args.command == "upsert":
        record = upsert_record(
            data,
            {
                "domain": args.domain,
                "account_ref": args.account_ref,
                "auth_type": args.auth_type,
                "signup_email": args.signup_email,
                "username": args.username,
                "credential_ref": args.credential_ref,
                "browser_profile_ref": args.browser_profile_ref,
                "mailbox_account": args.mailbox_account,
                "oauth_provider": args.oauth_provider,
                "created_at": args.created_at,
                "last_verified_at": args.last_verified_at,
                "status": args.status,
                "notes": args.note,
            },
        )
        save_registry(registry_path, data)
        print(json.dumps({"ok": True, "registry": str(registry_path), "record": record}, ensure_ascii=False, indent=2))
        return 0

    if args.command == "get":
        print(json.dumps({"ok": True, "record": get_record(data, args.domain)}, ensure_ascii=False, indent=2))
        return 0

    if args.command == "list":
        records = [normalize_record(item) for item in data["records"]]
        if args.auth_type:
            records = [item for item in records if item["auth_type"] == args.auth_type]
        if args.status:
            records = [item for item in records if item["status"] == args.status]
        print(json.dumps({"ok": True, "count": len(records), "records": records}, ensure_ascii=False, indent=2))
        return 0

    record = get_record(data, args.domain)
    record["last_verified_at"] = args.at or now_iso()
    if args.status:
        record["status"] = args.status
    upsert_record(data, record)
    save_registry(registry_path, data)
    print(json.dumps({"ok": True, "registry": str(registry_path), "record": record}, ensure_ascii=False, indent=2))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
