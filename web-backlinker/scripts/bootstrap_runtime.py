#!/usr/bin/env python3
from __future__ import annotations

import argparse
import json
from pathlib import Path

from common import default_base_dir, domain_from_url, now_iso, normalize_promoted_url, save_json, slugify
from preflight import run_preflight_checks


def build_run_id(campaign: str) -> str:
    stamp = now_iso().replace(":", "").replace("-", "").split(".")[0]
    return f"{stamp}-{slugify(campaign)}"


def main() -> int:
    parser = argparse.ArgumentParser(description="Create the runtime layout for a backlink campaign.")
    parser.add_argument("--base-dir", default=str(default_base_dir()))
    parser.add_argument("--campaign", default="backlink")
    parser.add_argument("--promoted-url", required=True)
    parser.add_argument("--run-id", default="")
    parser.add_argument("--waiting-config", action="store_true")
    parser.add_argument("--skip-preflight", action="store_true")
    parser.add_argument("--bb-mode", default="auto", choices=["auto", "openclaw", "standalone_extension", "mcp", "disabled"])
    args = parser.parse_args()

    base_dir = Path(args.base_dir).expanduser().resolve()
    run_id = args.run_id or build_run_id(args.campaign)
    promoted_url = normalize_promoted_url(args.promoted_url)
    promoted_domain = domain_from_url(promoted_url)
    created_at = now_iso()

    paths = {
        "accounts_dir": base_dir / "accounts",
        "artifacts_dir": base_dir / "artifacts" / run_id,
        "patterns_dir": base_dir / "playbooks" / "patterns",
        "sites_dir": base_dir / "playbooks" / "sites",
        "profiles_dir": base_dir / "profiles",
        "runs_dir": base_dir / "runs",
        "tasks_dir": base_dir / "tasks",
        "ledger_path": base_dir / "submission-ledger.json",
    }
    for path in paths.values():
        target = path if path.suffix else path
        target.mkdir(parents=True, exist_ok=True) if not target.suffix else target.parent.mkdir(parents=True, exist_ok=True)

    profile_path = paths["profiles_dir"] / f"{promoted_domain or run_id}.json"
    intake_path = paths["profiles_dir"] / f"{promoted_domain or run_id}.intake.json"
    task_store_path = paths["tasks_dir"] / f"{run_id}.json"
    manifest_path = paths["runs_dir"] / f"{run_id}.json"

    manifest = {
        "run_id": run_id,
        "campaign": args.campaign,
        "promoted_url": promoted_url,
        "promoted_domain": promoted_domain,
        "status": "WAITING_CONFIG" if args.waiting_config else "READY",
        "created_at": created_at,
        "updated_at": created_at,
        "intake": {
            "path": str(intake_path),
            "required_missing": [],
            "recommended_missing": [],
            "updated_at": "",
        },
        "preflight": {
            "generated_at": "",
            "bb_browser_mode": args.bb_mode,
            "default_provider": "dry-run",
            "ready_for_real_submit": False,
            "ready_for_verification": False,
            "blockers": [],
            "warnings": [],
            "checks": {},
        },
        "paths": {
            "base_dir": str(base_dir),
            "profile_path": str(profile_path),
            "intake_path": str(intake_path),
            "task_store_path": str(task_store_path),
            "manifest_path": str(manifest_path),
            "ledger_path": str(paths["ledger_path"]),
            "accounts_dir": str(paths["accounts_dir"]),
            "site_playbooks_dir": str(paths["sites_dir"]),
            "pattern_playbooks_dir": str(paths["patterns_dir"]),
            "artifacts_dir": str(paths["artifacts_dir"]),
        },
    }
    if not args.skip_preflight:
        manifest["preflight"] = run_preflight_checks(bb_mode=args.bb_mode)
    save_json(manifest_path, manifest)
    print(json.dumps({"ok": True, "manifest": manifest}, ensure_ascii=False, indent=2))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
