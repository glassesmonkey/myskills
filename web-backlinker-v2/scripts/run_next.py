#!/usr/bin/env python3
from __future__ import annotations

import argparse
import json
import subprocess
import sys
from datetime import datetime, timedelta, timezone
from pathlib import Path
from typing import Any

from common import load_json, now_iso, save_json
from task_store import (
    choose_claimable_task,
    events_path_for_store,
    find_task,
    load_store,
    normalize_task,
    release_stale_locks,
    save_store,
    upsert_ledger_record,
    load_ledger,
    save_ledger,
)


def run_json(argv: list[str], cwd: Path) -> dict[str, Any]:
    result = subprocess.run(argv, cwd=str(cwd), capture_output=True, text=True, check=False)
    if result.returncode != 0:
        message = result.stderr.strip() or result.stdout.strip() or f"command failed: {' '.join(argv)}"
        raise SystemExit(message)
    return json.loads(result.stdout)


def append_event(events_path: Path, event: dict[str, Any]) -> None:
    events_path.parent.mkdir(parents=True, exist_ok=True)
    with events_path.open("a", encoding="utf-8") as handle:
        handle.write(json.dumps(event, ensure_ascii=False) + "\n")


def claim_task(store_path: Path, worker_id: str, include_waiting_email: bool, lease_seconds: int) -> dict[str, Any] | None:
    data = load_store(store_path)
    release_stale_locks(data)
    candidate = choose_claimable_task(data, include_waiting_email)
    if not candidate:
        save_store(store_path, data)
        return None

    chosen = find_task(data, candidate["task_id"])
    lease_until = datetime.now(timezone.utc) + timedelta(seconds=lease_seconds)
    chosen["status"] = "RUNNING"
    chosen["attempts"] += 1
    chosen["locked_by"] = worker_id
    chosen["lock_expires_at"] = lease_until.isoformat()
    chosen["last_progress_at"] = now_iso()
    chosen["updated_at"] = now_iso()
    save_store(store_path, data)
    append_event(events_path_for_store(store_path), {"ts": now_iso(), "event": "claim", "task_id": chosen["task_id"], "worker_id": worker_id})
    return chosen


def checkpoint_task(store_path: Path, task_id: str, **updates: Any) -> dict[str, Any]:
    data = load_store(store_path)
    task = find_task(data, task_id)
    notes = updates.pop("notes", []) or []
    for key, value in updates.items():
        if value in ("", None):
            continue
        task[key] = value
    if notes:
        merged = [*(task.get("notes", []) or []), *[str(note).strip() for note in notes if str(note).strip()]]
        task["notes"] = merged[-12:]
    task["last_progress_at"] = now_iso()
    task["updated_at"] = now_iso()
    save_store(store_path, data)
    append_event(events_path_for_store(store_path), {"ts": now_iso(), "event": "checkpoint", "task_id": task_id, "phase": task.get("phase", "")})
    return normalize_task(task)


def finish_task(store_path: Path, task_id: str, result: str, note: list[str], listing_url: str = "", ledger_path: Path | None = None) -> dict[str, Any]:
    status_map = {
        "submitted": "DONE",
        "verified": "DONE",
        "already_listed": "DONE",
        "pending_email": "WAITING_EMAIL",
        "needs_human": "WAITING_HUMAN",
        "defer_retry": "RETRYABLE",
        "failed": "RETRYABLE",
        "skipped": "SKIPPED",
    }
    data = load_store(store_path)
    task = find_task(data, task_id)
    task["status"] = status_map[result]
    task["phase"] = result
    task["listing_url"] = listing_url or task.get("listing_url", "")
    task["locked_by"] = ""
    task["lock_expires_at"] = ""
    merged = [*(task.get("notes", []) or []), *[str(item).strip() for item in note if str(item).strip()]]
    task["notes"] = merged[-12:]
    task["last_progress_at"] = now_iso()
    task["updated_at"] = now_iso()

    if ledger_path and result in {"submitted", "verified", "already_listed", "pending_email"}:
        ledger = load_ledger(ledger_path)
        upsert_ledger_record(
            ledger=ledger,
            promoted_url=data.get("promoted_url", ""),
            target_domain=task.get("domain", ""),
            target_url=task.get("normalized_url", ""),
            state=result,
            run_id=data.get("run_id", ""),
            task_id=task["task_id"],
            listing_url=task.get("listing_url", ""),
            note="; ".join(task["notes"][-2:]),
        )
        save_ledger(ledger_path, ledger)

    save_store(store_path, data)
    append_event(events_path_for_store(store_path), {"ts": now_iso(), "event": "finish", "task_id": task_id, "result": result})
    return normalize_task(task)


def main() -> int:
    parser = argparse.ArgumentParser(description="Claim one backlink task, plan it, and execute or park it.")
    parser.add_argument("--manifest", required=True)
    parser.add_argument("--worker-id", default=f"worker-{datetime.now(timezone.utc).strftime('%Y%m%d%H%M%S')}")
    parser.add_argument("--provider", default="auto", choices=["auto", "browser-use-cli", "bb-browser", "dry-run", "manual"])
    parser.add_argument("--lease-seconds", type=int, default=900)
    parser.add_argument("--include-waiting-email", action="store_true")
    parser.add_argument("--deep-scout", action="store_true")
    parser.add_argument("--credentials", default="")
    parser.add_argument("--allow-waiting-config", action="store_true")
    args = parser.parse_args()

    repo_root = Path(__file__).resolve().parents[1]
    manifest_path = Path(args.manifest).expanduser().resolve()
    manifest = load_json(manifest_path, {})
    paths = manifest.get("paths", {})
    preflight = manifest.get("preflight", {}) or {}
    if manifest.get("status") == "WAITING_CONFIG" and not args.allow_waiting_config:
        print(
            json.dumps(
                {
                    "ok": False,
                    "reason": "waiting_config",
                    "message": "Run is blocked until required intake is filled.",
                    "required_missing": (manifest.get("intake") or {}).get("required_missing", []),
                    "intake_path": (manifest.get("paths") or {}).get("intake_path", ""),
                },
                ensure_ascii=False,
                indent=2,
            )
        )
        return 2
    checks = preflight.get("checks", {}) or {}
    bb_check = checks.get("bb_browser", {}) or {}
    browser_use_check = checks.get("browser_use", {}) or {}
    browser_runtime = (preflight.get("browser_runtime") or checks.get("browser_runtime") or {})
    bb_mode = preflight.get("bb_browser_mode", "auto")
    provider_name = args.provider if args.provider != "auto" else preflight.get("default_provider", "dry-run")

    if provider_name == "browser-use-cli" and preflight:
        if not browser_runtime.get("configured", False):
            print(
                json.dumps(
                    {
                        "ok": False,
                        "reason": "waiting_browser_runtime",
                        "message": "Shared CDP browser is not configured. Set BACKLINK_BROWSER_CDP_URL (or pass --cdp-url to preflight) and rerun preflight.",
                        "default_provider": preflight.get("default_provider", "dry-run"),
                        "warnings": preflight.get("warnings", []),
                    },
                    ensure_ascii=False,
                    indent=2,
                )
            )
            return 3
        if not browser_runtime.get("ok", False) or not browser_use_check.get("smoke_ok", False):
            print(
                json.dumps(
                    {
                        "ok": False,
                        "reason": "waiting_browser",
                        "message": "browser-use CLI is not ready for shared-CDP execution. Rerun preflight or use --provider dry-run/manual explicitly.",
                        "default_provider": preflight.get("default_provider", "dry-run"),
                        "warnings": preflight.get("warnings", []),
                        "browser_runtime": browser_runtime,
                        "browser_use": {
                            "installed": browser_use_check.get("installed", False),
                            "smoke_ok": browser_use_check.get("smoke_ok", False),
                            "smoke_error": browser_use_check.get("smoke_error", ""),
                        },
                    },
                    ensure_ascii=False,
                    indent=2,
                )
            )
            return 3
    elif provider_name == "bb-browser" and preflight:
        if not bb_check.get("mode_allowed", True):
            print(
                json.dumps(
                    {
                        "ok": False,
                        "reason": "waiting_browser_mode",
                        "message": bb_check.get("smoke_error", "bb-browser mode is not supported in the current host runtime."),
                        "bb_browser_mode": bb_mode,
                        "host_runtime": bb_check.get("host_runtime", preflight.get("host_runtime", "unknown")),
                    },
                    ensure_ascii=False,
                    indent=2,
                )
            )
            return 4
        if bb_mode == "mcp":
            print(
                json.dumps(
                    {
                        "ok": False,
                        "reason": "waiting_browser_mode",
                        "message": "bb-browser is configured for MCP mode. This worker only supports direct CLI modes right now.",
                        "bb_browser_mode": bb_mode,
                    },
                    ensure_ascii=False,
                    indent=2,
                )
            )
            return 4
        if not bb_check.get("smoke_ok", False):
            print(
                json.dumps(
                    {
                        "ok": False,
                        "reason": "waiting_browser",
                        "message": "bb-browser is not ready for real-submit mode. Rerun preflight or use --provider dry-run/manual explicitly.",
                        "bb_browser_mode": bb_mode,
                        "default_provider": preflight.get("default_provider", "dry-run"),
                        "warnings": preflight.get("warnings", []),
                        "bb_browser": {
                            "installed": bb_check.get("installed", False),
                            "smoke_ok": bb_check.get("smoke_ok", False),
                            "smoke_error": bb_check.get("smoke_error", ""),
                        },
                    },
                    ensure_ascii=False,
                    indent=2,
                )
            )
            return 3
    store_path = Path(paths["task_store_path"]).expanduser().resolve()
    profile_path = Path(paths["profile_path"]).expanduser().resolve()
    intake_path = Path(paths.get("intake_path") or profile_path.with_suffix('.intake.json')).expanduser().resolve()
    base_dir = Path(paths["base_dir"]).expanduser().resolve()
    artifacts_dir = Path(paths["artifacts_dir"]).expanduser().resolve()
    ledger_path = Path(paths["ledger_path"]).expanduser().resolve()
    task = claim_task(store_path, args.worker_id, args.include_waiting_email, args.lease_seconds)

    if not task:
        print(json.dumps({"ok": True, "task": None, "message": "no executable tasks"}, ensure_ascii=False, indent=2))
        return 0

    try:
        scout_path = artifacts_dir / f"{task['task_id']}-scout.json"
        scout_command = [
            sys.executable,
            str(repo_root / "scripts" / "scout_target.py"),
            "--url",
            task["normalized_url"],
            "--out",
            str(scout_path),
        ]
        if args.deep_scout:
            scout_command.append("--deep")
        scout_result = run_json(scout_command, cwd=repo_root)
        scout = scout_result.get("result", scout_result)
        task = checkpoint_task(
            store_path,
            task["task_id"],
            phase="scouted",
            site_type=scout.get("site_type", "unknown"),
            auth_type=scout.get("auth_type", "unknown"),
            submission_type=scout.get("submission_type", "unknown"),
            requires_login=scout.get("requires_login", False),
            oauth_providers=scout.get("oauth_providers", []),
            captcha_tier=scout.get("captcha_tier", "unknown"),
            anti_bot=scout.get("anti_bot", "unknown"),
            blocker_type=scout.get("blocker_type", ""),
            requires_reciprocal_backlink=scout.get("requires_reciprocal_backlink", False),
            submission_url=scout.get("candidate_submit_url", ""),
            notes=scout.get("notes", []),
        )

        playbook_candidate = base_dir / "playbooks" / "sites" / f"{task['domain'].replace('www.', '')}.json"
        if not playbook_candidate.exists() and scout.get("forms"):
            run_json(
                [
                    sys.executable,
                    str(repo_root / "scripts" / "scaffold_playbook.py"),
                    "--scout-file",
                    str(scout_path),
                ],
                cwd=repo_root,
            )

        plan_result = run_json(
            [
                sys.executable,
                str(repo_root / "scripts" / "select_execution_plan.py"),
                "--store",
                str(store_path),
                "--task-id",
                task["task_id"],
                "--base-dir",
                str(base_dir),
                "--intake",
                str(intake_path),
                "--apply",
            ],
            cwd=repo_root,
        )
        plan = plan_result["plan"]
        plan_path = artifacts_dir / f"{task['task_id']}-plan.json"
        save_json(plan_path, plan)

        brief_path = artifacts_dir / f"{task['task_id']}-brief.json"
        run_json(
            [
                sys.executable,
                str(repo_root / "scripts" / "prepare_worker_brief.py"),
                "--store",
                str(store_path),
                "--task-id",
                task["task_id"],
                "--profile",
                str(profile_path),
                "--base-dir",
                str(base_dir),
                "--out",
                str(brief_path),
            ],
            cwd=repo_root,
        )

        task_path = artifacts_dir / f"{task['task_id']}-task.json"
        current_task = find_task(load_store(store_path), task["task_id"])
        save_json(task_path, current_task)

        if plan["automation_disposition"] == "AUTO_SKIP":
            skipped = finish_task(
                store_path,
                task["task_id"],
                "skipped",
                note=[f"skipped by plan: {plan['next_action']}", *plan.get("rationale", [])],
                ledger_path=ledger_path,
            )
            print(json.dumps({"ok": True, "task": skipped, "executed": False, "reason": "auto_skip"}, ensure_ascii=False, indent=2))
            return 0

        if plan["automation_disposition"] != "AUTO_EXECUTE":
            parked = finish_task(
                store_path,
                task["task_id"],
                "needs_human",
                note=[f"parked by plan: {plan['next_action']}", *plan.get("rationale", [])],
                ledger_path=ledger_path,
            )
            print(json.dumps({"ok": True, "task": parked, "executed": False, "reason": "automation_disposition"}, ensure_ascii=False, indent=2))
            return 0

        credentials_file = Path(args.credentials).expanduser().resolve() if args.credentials else ""
        execution_result = run_json(
            [
                "node",
                str(repo_root / "packages" / "execution-core" / "src" / "cli.js"),
                "submit",
                "--task-file",
                str(task_path),
                "--brief-file",
                str(brief_path),
                "--plan-file",
                str(plan_path),
                "--provider",
                provider_name,
                "--bb-mode",
                preflight.get("bb_browser_mode", "auto"),
                *(["--cdp-url", str(browser_runtime.get("cdp_url", ""))] if browser_runtime.get("cdp_url") else []),
                *(["--playwright-ws-url", str(browser_runtime.get("playwright_ws_url", ""))] if browser_runtime.get("playwright_ws_url") else []),
                *(["--credentials-file", str(credentials_file)] if credentials_file else []),
                "--out",
                str(artifacts_dir / f"{task['task_id']}-execution.json"),
            ],
            cwd=repo_root,
        )
        result = execution_result["result"]
        notes = [result.get("confirmation_text", ""), *(result.get("notes", []) or [])]
        final_task = finish_task(
            store_path,
            task["task_id"],
            result=result["outcome"],
            note=notes,
            listing_url=result.get("listing_url", ""),
            ledger_path=ledger_path,
        )
        print(json.dumps({"ok": True, "task": final_task, "executed": True, "provider": execution_result.get("provider", "")}, ensure_ascii=False, indent=2))
        return 0
    except Exception as error:
        failed = finish_task(
            store_path,
            task["task_id"],
            "defer_retry",
            note=[f"worker error: {error}"],
            ledger_path=ledger_path,
        )
        print(json.dumps({"ok": False, "task": failed, "error": str(error)}, ensure_ascii=False, indent=2))
        return 1


if __name__ == "__main__":
    raise SystemExit(main())
