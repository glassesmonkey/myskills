#!/usr/bin/env python3
from __future__ import annotations

import argparse
import json
from datetime import datetime, timedelta, timezone
from pathlib import Path
from typing import Any

from common import (
    append_jsonl,
    default_base_dir,
    domain_from_url,
    load_json,
    normalize_promoted_url,
    normalize_url,
    now_iso,
    read_targets_file,
    save_json,
    unique_notes,
)


ACTIVE_LEDGER_STATES = {"submitted", "pending_email", "verified", "already_listed"}
CLAIM_ORDER = {"READY": 0, "RETRYABLE": 1, "WAITING_EMAIL": 2}
RESULT_TO_STATUS = {
    "submitted": "DONE",
    "pending_email": "WAITING_EMAIL",
    "verified": "DONE",
    "already_listed": "DONE",
    "needs_human": "WAITING_HUMAN",
    "defer_retry": "RETRYABLE",
    "failed": "RETRYABLE",
    "skipped": "SKIPPED",
}


def default_tasks_dir() -> Path:
    return default_base_dir() / "tasks"


def default_ledger_path() -> Path:
    return default_base_dir() / "submission-ledger.json"


def parse_ts(value: str) -> datetime | None:
    if not value:
        return None
    try:
        return datetime.fromisoformat(value.replace("Z", "+00:00"))
    except Exception:
        return None


def coerce_bool(value: str | None) -> bool | None:
    if value is None:
        return None
    lowered = value.strip().lower()
    if lowered in {"1", "true", "yes", "y"}:
        return True
    if lowered in {"0", "false", "no", "n"}:
        return False
    raise SystemExit(f"invalid boolean value: {value!r}")


def events_path_for_store(path: Path) -> Path:
    return path.with_suffix(".events.jsonl")


def load_store(path: Path) -> dict[str, Any]:
    data = load_json(
        path,
        {
            "run_id": "",
            "promoted_url": "",
            "created_at": "",
            "updated_at": "",
            "tasks": [],
        },
    )
    data.setdefault("tasks", [])
    return data


def save_store(path: Path, data: dict[str, Any]) -> None:
    data["updated_at"] = now_iso()
    save_json(path, data)


def normalize_task(task: dict[str, Any]) -> dict[str, Any]:
    updated_at = str(task.get("updated_at", "")).strip() or now_iso()
    normalized = {
        "task_id": str(task.get("task_id", "")).strip(),
        "row_id": str(task.get("row_id", "")).strip(),
        "input_url": str(task.get("input_url", "")).strip(),
        "normalized_url": normalize_url(task.get("normalized_url") or task.get("input_url", "")),
        "domain": str(task.get("domain", "")).strip().lower() or domain_from_url(task.get("normalized_url") or task.get("input_url", "")),
        "status": str(task.get("status", "READY")).strip().upper() or "READY",
        "phase": str(task.get("phase", "imported")).strip() or "imported",
        "attempts": int(task.get("attempts", 0) or 0),
        "site_type": str(task.get("site_type", "unknown")).strip() or "unknown",
        "auth_type": str(task.get("auth_type", "unknown")).strip() or "unknown",
        "submission_type": str(task.get("submission_type", "unknown")).strip() or "unknown",
        "requires_login": bool(task.get("requires_login", False)),
        "captcha_tier": str(task.get("captcha_tier", "unknown")).strip() or "unknown",
        "anti_bot": str(task.get("anti_bot", "unknown")).strip() or "unknown",
        "route": str(task.get("route", "")).strip(),
        "execution_mode": str(task.get("execution_mode", "")).strip(),
        "automation_disposition": str(task.get("automation_disposition", "")).strip(),
        "playbook_id": str(task.get("playbook_id", "")).strip(),
        "playbook_confidence": float(task.get("playbook_confidence", 0.0) or 0.0),
        "account_ref": str(task.get("account_ref", "")).strip(),
        "ledger_state": str(task.get("ledger_state", "")).strip().lower(),
        "submission_url": str(task.get("submission_url", "")).strip(),
        "listing_url": str(task.get("listing_url", "")).strip(),
        "last_error": str(task.get("last_error", "")).strip(),
        "last_progress_at": str(task.get("last_progress_at", "")).strip() or updated_at,
        "updated_at": updated_at,
        "locked_by": str(task.get("locked_by", "")).strip(),
        "lock_expires_at": str(task.get("lock_expires_at", "")).strip(),
        "notes": unique_notes(task.get("notes", [])),
    }
    if not normalized["task_id"]:
        normalized["task_id"] = f"task-{normalized['row_id'] or normalized['domain'] or 'unknown'}"
    return normalized


def find_task(data: dict[str, Any], task_id: str) -> dict[str, Any]:
    for index, task in enumerate(data["tasks"]):
        normalized = normalize_task(task)
        data["tasks"][index] = normalized
        if normalized["task_id"] == task_id:
            return normalized
    raise SystemExit(f"task not found: {task_id}")


def load_ledger(path: Path) -> dict[str, Any]:
    data = load_json(path, {"updated_at": "", "records": []})
    if isinstance(data, list):
        data = {"updated_at": "", "records": data}
    data.setdefault("records", [])
    return data


def save_ledger(path: Path, data: dict[str, Any]) -> None:
    data["updated_at"] = now_iso()
    save_json(path, data)


def find_ledger_match(ledger: dict[str, Any], promoted_url: str, domain: str, normalized_target_url: str) -> dict[str, Any] | None:
    promoted_key = normalize_promoted_url(promoted_url)
    normalized_target = normalize_url(normalized_target_url)
    for record in ledger.get("records", []):
        if str(record.get("state", "")).strip().lower() not in ACTIVE_LEDGER_STATES:
            continue
        if normalize_promoted_url(record.get("promoted_url", "")) != promoted_key:
            continue
        record_domain = str(record.get("target_domain", "")).strip().lower()
        record_url = normalize_url(record.get("target_normalized_url", ""))
        if domain and record_domain == domain:
            return record
        if normalized_target and record_url == normalized_target:
            return record
    return None


def upsert_ledger_record(
    ledger: dict[str, Any],
    promoted_url: str,
    target_domain: str,
    target_url: str,
    state: str,
    run_id: str,
    task_id: str,
    listing_url: str,
    note: str,
) -> dict[str, Any]:
    match = find_ledger_match(ledger, promoted_url, target_domain, target_url)
    timestamp = now_iso()
    if match:
        match.update(
            {
                "state": state,
                "updated_at": timestamp,
                "run_id": run_id,
                "task_id": task_id,
                "listing_url": listing_url,
                "note": note,
            }
        )
        return match
    record = {
        "promoted_url": normalize_promoted_url(promoted_url),
        "promoted_domain": domain_from_url(promoted_url),
        "target_domain": target_domain,
        "target_normalized_url": normalize_url(target_url),
        "state": state,
        "first_seen_at": timestamp,
        "updated_at": timestamp,
        "run_id": run_id,
        "task_id": task_id,
        "listing_url": listing_url,
        "note": note,
    }
    ledger.setdefault("records", []).append(record)
    return record


def release_stale_locks(data: dict[str, Any]) -> int:
    changed = 0
    now_value = datetime.now(timezone.utc)
    for index, task in enumerate(data["tasks"]):
        normalized = normalize_task(task)
        expires_at = parse_ts(normalized["lock_expires_at"])
        if normalized["locked_by"] and expires_at and expires_at <= now_value:
            normalized["locked_by"] = ""
            normalized["lock_expires_at"] = ""
            if normalized["status"] == "RUNNING":
                normalized["status"] = "RETRYABLE"
            normalized["updated_at"] = now_iso()
            data["tasks"][index] = normalized
            changed += 1
        else:
            data["tasks"][index] = normalized
    return changed


def choose_claimable_task(data: dict[str, Any], include_waiting_email: bool) -> dict[str, Any] | None:
    allowed = {"READY", "RETRYABLE"}
    if include_waiting_email:
        allowed.add("WAITING_EMAIL")
    candidates = []
    for task in data["tasks"]:
        normalized = normalize_task(task)
        if normalized["status"] not in allowed or normalized["locked_by"]:
            continue
        candidates.append(normalized)
    if not candidates:
        return None
    candidates.sort(key=lambda task: (CLAIM_ORDER.get(task["status"], 99), task["attempts"], task["row_id"], task["task_id"]))
    return candidates[0]


def main() -> int:
    parser = argparse.ArgumentParser(description="Persist and manage resumable backlink tasks.")
    parser.add_argument("--store", default="")
    sub = parser.add_subparsers(dest="command", required=True)

    init = sub.add_parser("init")
    init.add_argument("--run-id", required=True)
    init.add_argument("--targets-file", required=True)
    init.add_argument("--promoted-url", required=True)
    init.add_argument("--submission-ledger", default=str(default_ledger_path()))

    claim = sub.add_parser("claim")
    claim.add_argument("--worker-id", required=True)
    claim.add_argument("--lease-seconds", type=int, default=900)
    claim.add_argument("--include-waiting-email", action="store_true")

    get = sub.add_parser("get")
    get.add_argument("--task-id", required=True)

    checkpoint = sub.add_parser("checkpoint")
    checkpoint.add_argument("--task-id", required=True)
    checkpoint.add_argument("--status", default="")
    checkpoint.add_argument("--phase", default="")
    checkpoint.add_argument("--site-type", default="")
    checkpoint.add_argument("--auth-type", default="")
    checkpoint.add_argument("--submission-type", default="")
    checkpoint.add_argument("--requires-login", default=None)
    checkpoint.add_argument("--captcha-tier", default="")
    checkpoint.add_argument("--anti-bot", default="")
    checkpoint.add_argument("--route", default="")
    checkpoint.add_argument("--execution-mode", default="")
    checkpoint.add_argument("--automation-disposition", default="")
    checkpoint.add_argument("--playbook-id", default="")
    checkpoint.add_argument("--playbook-confidence", type=float, default=None)
    checkpoint.add_argument("--account-ref", default="")
    checkpoint.add_argument("--submission-url", default="")
    checkpoint.add_argument("--listing-url", default="")
    checkpoint.add_argument("--last-error", default="")
    checkpoint.add_argument("--note", action="append", default=[])

    finish = sub.add_parser("finish")
    finish.add_argument("--task-id", required=True)
    finish.add_argument(
        "--result",
        choices=sorted(RESULT_TO_STATUS),
        required=True,
    )
    finish.add_argument("--submission-ledger", default=str(default_ledger_path()))
    finish.add_argument("--listing-url", default="")
    finish.add_argument("--note", action="append", default=[])

    summary = sub.add_parser("summary")
    release = sub.add_parser("release-stale")

    args = parser.parse_args()
    store_path = Path(args.store).expanduser().resolve() if args.store else default_tasks_dir() / f"{getattr(args, 'run_id', '')}.json"
    events_path = events_path_for_store(store_path)

    if args.command == "init":
        ledger = load_ledger(Path(args.submission_ledger).expanduser().resolve())
        targets = read_targets_file(Path(args.targets_file).expanduser().resolve())
        seen: set[str] = set()
        tasks = []
        for index, raw in enumerate(targets, start=1):
            normalized_url = normalize_url(raw)
            if not normalized_url or normalized_url in seen:
                continue
            seen.add(normalized_url)
            domain = domain_from_url(normalized_url)
            ledger_match = find_ledger_match(ledger, args.promoted_url, domain, normalized_url)
            task = normalize_task(
                {
                    "task_id": f"task-{index:04d}",
                    "row_id": f"row-{index:04d}",
                    "input_url": raw,
                    "normalized_url": normalized_url,
                    "domain": domain,
                    "status": "SKIPPED" if ledger_match else "READY",
                    "phase": "already_recorded" if ledger_match else "imported",
                    "ledger_state": str(ledger_match.get("state", "")).strip().lower() if ledger_match else "",
                    "notes": [f"already {ledger_match['state']} for promoted site"] if ledger_match else [],
                }
            )
            tasks.append(task)
        data = {
            "run_id": args.run_id,
            "promoted_url": normalize_promoted_url(args.promoted_url),
            "created_at": now_iso(),
            "updated_at": now_iso(),
            "tasks": tasks,
        }
        save_store(store_path, data)
        append_jsonl(events_path, {"ts": now_iso(), "event": "init", "run_id": args.run_id, "count": len(tasks)})
        print(json.dumps({"ok": True, "store": str(store_path), "count": len(tasks)}, ensure_ascii=False, indent=2))
        return 0

    data = load_store(store_path)

    if args.command == "claim":
        released = release_stale_locks(data)
        candidate = choose_claimable_task(data, args.include_waiting_email)
        if not candidate:
            save_store(store_path, data)
            print(json.dumps({"ok": False, "store": str(store_path), "released": released, "task": None}, ensure_ascii=False, indent=2))
            return 1
        lease_until = datetime.now(timezone.utc) + timedelta(seconds=args.lease_seconds)
        chosen = find_task(data, candidate["task_id"])
        chosen["locked_by"] = args.worker_id
        chosen["lock_expires_at"] = lease_until.isoformat()
        chosen["status"] = "RUNNING"
        chosen["attempts"] += 1
        chosen["last_progress_at"] = now_iso()
        chosen["updated_at"] = now_iso()
        save_store(store_path, data)
        append_jsonl(events_path, {"ts": now_iso(), "event": "claim", "task_id": chosen["task_id"], "worker_id": args.worker_id})
        print(json.dumps({"ok": True, "store": str(store_path), "released": released, "task": chosen}, ensure_ascii=False, indent=2))
        return 0

    if args.command == "get":
        task = find_task(data, args.task_id)
        print(json.dumps({"ok": True, "task": task}, ensure_ascii=False, indent=2))
        return 0

    if args.command == "checkpoint":
        task = find_task(data, args.task_id)
        if args.status:
            task["status"] = args.status.strip().upper()
        if args.phase:
            task["phase"] = args.phase
        if args.site_type:
            task["site_type"] = args.site_type
        if args.auth_type:
            task["auth_type"] = args.auth_type
        if args.submission_type:
            task["submission_type"] = args.submission_type
        requires_login = coerce_bool(args.requires_login)
        if requires_login is not None:
            task["requires_login"] = requires_login
        if args.captcha_tier:
            task["captcha_tier"] = args.captcha_tier
        if args.anti_bot:
            task["anti_bot"] = args.anti_bot
        if args.route:
            task["route"] = args.route
        if args.execution_mode:
            task["execution_mode"] = args.execution_mode
        if args.automation_disposition:
            task["automation_disposition"] = args.automation_disposition
        if args.playbook_id:
            task["playbook_id"] = args.playbook_id
        if args.playbook_confidence is not None:
            task["playbook_confidence"] = args.playbook_confidence
        if args.account_ref:
            task["account_ref"] = args.account_ref
        if args.submission_url:
            task["submission_url"] = args.submission_url
        if args.listing_url:
            task["listing_url"] = args.listing_url
        if args.last_error:
            task["last_error"] = args.last_error
        task["notes"] = unique_notes([*(task.get("notes", []) or []), *args.note])
        task["last_progress_at"] = now_iso()
        task["updated_at"] = now_iso()
        save_store(store_path, data)
        append_jsonl(events_path, {"ts": now_iso(), "event": "checkpoint", "task_id": task["task_id"], "phase": task["phase"]})
        print(json.dumps({"ok": True, "task": task}, ensure_ascii=False, indent=2))
        return 0

    if args.command == "finish":
        task = find_task(data, args.task_id)
        task["status"] = RESULT_TO_STATUS[args.result]
        task["phase"] = args.result
        task["ledger_state"] = args.result if args.result in ACTIVE_LEDGER_STATES else task.get("ledger_state", "")
        task["listing_url"] = args.listing_url or task.get("listing_url", "")
        task["notes"] = unique_notes([*(task.get("notes", []) or []), *args.note])
        task["locked_by"] = ""
        task["lock_expires_at"] = ""
        task["last_progress_at"] = now_iso()
        task["updated_at"] = now_iso()
        if args.result in ACTIVE_LEDGER_STATES:
            ledger_path = Path(args.submission_ledger).expanduser().resolve()
            ledger = load_ledger(ledger_path)
            upsert_ledger_record(
                ledger=ledger,
                promoted_url=data.get("promoted_url", ""),
                target_domain=task["domain"],
                target_url=task["normalized_url"],
                state=args.result,
                run_id=data.get("run_id", ""),
                task_id=task["task_id"],
                listing_url=task["listing_url"],
                note="; ".join(task["notes"][-2:]),
            )
            save_ledger(ledger_path, ledger)
        save_store(store_path, data)
        append_jsonl(events_path, {"ts": now_iso(), "event": "finish", "task_id": task["task_id"], "result": args.result})
        print(json.dumps({"ok": True, "task": task}, ensure_ascii=False, indent=2))
        return 0

    if args.command == "release-stale":
        released = release_stale_locks(data)
        save_store(store_path, data)
        append_jsonl(events_path, {"ts": now_iso(), "event": "release_stale", "released": released})
        print(json.dumps({"ok": True, "released": released}, ensure_ascii=False, indent=2))
        return 0

    released = release_stale_locks(data)
    save_store(store_path, data)
    counts: dict[str, int] = {}
    for task in data["tasks"]:
        status = normalize_task(task)["status"]
        counts[status] = counts.get(status, 0) + 1
    print(json.dumps({"ok": True, "released": released, "counts": counts, "total": len(data["tasks"])}, ensure_ascii=False, indent=2))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
