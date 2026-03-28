#!/usr/bin/env python3
from __future__ import annotations

import argparse
import json
import os
import subprocess
import sys
import time
from datetime import datetime, timedelta, timezone
from pathlib import Path
from typing import Any

from common import append_jsonl, load_json, now_iso, save_json


def parse_ts(value: str) -> datetime | None:
    if not value:
        return None
    try:
        return datetime.fromisoformat(str(value).replace("Z", "+00:00"))
    except Exception:
        return None


def make_lock_payload(run_id: str, owner: str, ttl_seconds: int) -> dict[str, Any]:
    now_value = datetime.now(timezone.utc)
    return {
        "run_id": run_id,
        "owner": owner,
        "acquired_at": now_value.isoformat(),
        "expires_at": (now_value + timedelta(seconds=ttl_seconds)).isoformat(),
        "pid": os.getpid(),
        "host": os.uname().nodename if hasattr(os, "uname") else "unknown",
    }


def acquire_lock(lock_path: Path, run_id: str, owner: str, ttl_seconds: int) -> tuple[bool, dict[str, Any]]:
    existing = load_json(lock_path, {})
    expires_at = parse_ts(str(existing.get("expires_at", ""))) if existing else None
    now_value = datetime.now(timezone.utc)
    if existing and expires_at and expires_at > now_value:
        return False, existing
    payload = make_lock_payload(run_id=run_id, owner=owner, ttl_seconds=ttl_seconds)
    save_json(lock_path, payload)
    return True, payload


def refresh_lock(lock_path: Path, run_id: str, owner: str, ttl_seconds: int) -> dict[str, Any]:
    payload = make_lock_payload(run_id=run_id, owner=owner, ttl_seconds=ttl_seconds)
    save_json(lock_path, payload)
    return payload


def release_lock(lock_path: Path, owner: str) -> None:
    existing = load_json(lock_path, {})
    if existing and str(existing.get("owner", "")).strip() == owner and lock_path.exists():
        lock_path.unlink()


def events_path_for_run(run_id: str, base_dir: Path) -> Path:
    return base_dir / "runs" / f"{run_id}.batch-events.jsonl"


def run_once(
    repo_root: Path,
    manifest_path: Path,
    provider: str,
    worker_id: str,
    timeout_seconds: int,
    lease_seconds: int,
    include_waiting_email: bool,
    deep_scout: bool,
    credentials: str,
    allow_waiting_config: bool,
) -> dict[str, Any]:
    command = [
        sys.executable,
        str(repo_root / "scripts" / "run_next.py"),
        "--manifest",
        str(manifest_path),
        "--provider",
        provider,
        "--worker-id",
        worker_id,
        "--lease-seconds",
        str(lease_seconds),
    ]
    if include_waiting_email:
        command.append("--include-waiting-email")
    if deep_scout:
        command.append("--deep-scout")
    if credentials:
        command.extend(["--credentials", credentials])
    if allow_waiting_config:
        command.append("--allow-waiting-config")

    try:
        result = subprocess.run(
            command,
            cwd=str(repo_root),
            capture_output=True,
            text=True,
            timeout=timeout_seconds,
            check=False,
        )
    except subprocess.TimeoutExpired:
        return {
            "ok": False,
            "timed_out": True,
            "returncode": None,
            "stdout": "",
            "stderr": f"run_next timed out after {timeout_seconds}s",
            "payload": {},
        }

    payload: dict[str, Any] = {}
    stdout = (result.stdout or "").strip()
    if stdout:
        try:
            payload = json.loads(stdout)
        except json.JSONDecodeError:
            payload = {"raw_stdout": stdout[:4000]}

    return {
        "ok": result.returncode == 0,
        "timed_out": False,
        "returncode": result.returncode,
        "stdout": stdout,
        "stderr": (result.stderr or "").strip(),
        "payload": payload,
    }


def main() -> int:
    parser = argparse.ArgumentParser(description="Run a small serial batch of backlink tasks with a run-level single-flight lock.")
    parser.add_argument("--manifest", required=True)
    parser.add_argument("--provider", default="auto", choices=["auto", "browser-use-cli", "bb-browser", "dry-run", "manual"])
    parser.add_argument("--max-tasks", type=int, default=3)
    parser.add_argument("--max-seconds", type=int, default=1320)
    parser.add_argument("--task-timeout", type=int, default=480)
    parser.add_argument("--lease-seconds", type=int, default=540)
    parser.add_argument("--lock-ttl-seconds", type=int, default=1800)
    parser.add_argument("--worker-prefix", default="batch")
    parser.add_argument("--credentials", default="")
    parser.add_argument("--include-waiting-email", action="store_true")
    parser.add_argument("--deep-scout", action="store_true")
    parser.add_argument("--allow-waiting-config", action="store_true")
    args = parser.parse_args()

    repo_root = Path(__file__).resolve().parents[1]
    manifest_path = Path(args.manifest).expanduser().resolve()
    manifest = load_json(manifest_path, {})
    if not manifest:
        raise SystemExit(f"manifest not found: {manifest_path}")

    run_id = str(manifest.get("run_id", "")).strip() or manifest_path.stem
    paths = manifest.get("paths", {}) or {}
    base_dir = Path(paths.get("base_dir") or (repo_root / "data" / "backlink-helper")).expanduser().resolve()
    locks_dir = base_dir / "locks"
    lock_path = locks_dir / f"{run_id}.batch.lock.json"
    owner = f"{args.worker_prefix}-{datetime.now(timezone.utc).strftime('%Y%m%d%H%M%S')}-{os.getpid()}"
    events_path = events_path_for_run(run_id, base_dir)

    acquired, lock_payload = acquire_lock(lock_path, run_id=run_id, owner=owner, ttl_seconds=args.lock_ttl_seconds)
    if not acquired:
        payload = {
            "ok": True,
            "executed": False,
            "reason": "lock_held",
            "run_id": run_id,
            "lock": lock_payload,
            "message": "another batch worker is still active",
        }
        print(json.dumps(payload, ensure_ascii=False, indent=2))
        return 0

    append_jsonl(events_path, {"ts": now_iso(), "event": "batch_start", "run_id": run_id, "owner": owner, "args": {
        "max_tasks": args.max_tasks,
        "max_seconds": args.max_seconds,
        "task_timeout": args.task_timeout,
        "provider": args.provider,
    }})

    started = time.monotonic()
    deadline = started + max(args.max_seconds, 1)
    completed: list[dict[str, Any]] = []
    exit_reason = "budget_exhausted"
    exit_code = 0

    try:
        for index in range(args.max_tasks):
            refresh_lock(lock_path, run_id=run_id, owner=owner, ttl_seconds=args.lock_ttl_seconds)
            remaining = int(deadline - time.monotonic())
            if remaining <= 0:
                exit_reason = "batch_timeout"
                break

            per_task_timeout = min(args.task_timeout, remaining)
            worker_id = f"{owner}-task{index + 1}"
            attempt = run_once(
                repo_root=repo_root,
                manifest_path=manifest_path,
                provider=args.provider,
                worker_id=worker_id,
                timeout_seconds=per_task_timeout,
                lease_seconds=args.lease_seconds,
                include_waiting_email=args.include_waiting_email,
                deep_scout=args.deep_scout,
                credentials=args.credentials,
                allow_waiting_config=args.allow_waiting_config,
            )

            payload = attempt.get("payload", {}) or {}
            task = payload.get("task") if isinstance(payload, dict) else None
            record = {
                "index": index + 1,
                "worker_id": worker_id,
                "returncode": attempt.get("returncode"),
                "timed_out": attempt.get("timed_out", False),
                "ok": attempt.get("ok", False),
                "reason": payload.get("reason", "") if isinstance(payload, dict) else "",
                "provider": payload.get("provider", "") if isinstance(payload, dict) else "",
                "task": {
                    "task_id": task.get("task_id", "") if isinstance(task, dict) else "",
                    "domain": task.get("domain", "") if isinstance(task, dict) else "",
                    "status": task.get("status", "") if isinstance(task, dict) else "",
                    "phase": task.get("phase", "") if isinstance(task, dict) else "",
                },
                "stderr": attempt.get("stderr", "")[:1000],
            }
            completed.append(record)
            append_jsonl(events_path, {"ts": now_iso(), "event": "batch_step", "run_id": run_id, "owner": owner, **record})

            if attempt.get("timed_out"):
                exit_reason = "task_timeout"
                exit_code = 1
                break

            if isinstance(payload, dict) and payload.get("reason") == "waiting_config":
                exit_reason = "waiting_config"
                exit_code = 2
                break

            if isinstance(payload, dict) and payload.get("task") is None:
                exit_reason = "no_tasks"
                break

            if not attempt.get("ok", False):
                exit_reason = "worker_error"
                exit_code = 1
                break

        else:
            exit_reason = "max_tasks_reached"
    finally:
        append_jsonl(events_path, {
            "ts": now_iso(),
            "event": "batch_finish",
            "run_id": run_id,
            "owner": owner,
            "exit_reason": exit_reason,
            "processed": len([item for item in completed if item.get("task", {}).get("task_id")]),
            "steps": len(completed),
            "elapsed_seconds": round(time.monotonic() - started, 2),
        })
        release_lock(lock_path, owner)

    print(
        json.dumps(
            {
                "ok": exit_code == 0,
                "run_id": run_id,
                "owner": owner,
                "executed": True,
                "exit_reason": exit_reason,
                "processed": len([item for item in completed if item.get("task", {}).get("task_id")]),
                "steps": len(completed),
                "elapsed_seconds": round(time.monotonic() - started, 2),
                "results": completed,
            },
            ensure_ascii=False,
            indent=2,
        )
    )
    return exit_code


if __name__ == "__main__":
    raise SystemExit(main())
