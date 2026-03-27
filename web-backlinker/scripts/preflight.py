#!/usr/bin/env python3
from __future__ import annotations

import argparse
import json
import os
import shutil
import subprocess
from pathlib import Path
from typing import Any, Callable

from common import now_iso, save_json, load_json


CommandRunner = Callable[[list[str], int], dict[str, Any]]
BB_MODES = {"auto", "openclaw", "standalone_extension", "mcp", "disabled"}


def run_command(argv: list[str], timeout: int = 8) -> dict[str, Any]:
    try:
        result = subprocess.run(argv, capture_output=True, text=True, check=False, timeout=timeout)
        return {
            "ok": result.returncode == 0,
            "code": result.returncode,
            "stdout": result.stdout.strip(),
            "stderr": result.stderr.strip(),
            "timed_out": False,
        }
    except subprocess.TimeoutExpired as error:
        return {
            "ok": False,
            "code": None,
            "stdout": (error.stdout or "").strip(),
            "stderr": (error.stderr or "").strip(),
            "timed_out": True,
        }


def first_line(text: str) -> str:
    return str(text or "").splitlines()[0].strip()


def parse_gog_status(output: str) -> dict[str, str]:
    data: dict[str, str] = {}
    for line in str(output or "").splitlines():
        if "\t" not in line:
            continue
        key, value = line.split("\t", 1)
        data[key.strip()] = value.strip()
    return data


def detect_host_runtime(env: dict[str, str] | None = None) -> str:
    environment = env or os.environ
    if environment.get("CODEX_THREAD_ID") or environment.get("CODEX_CI") or environment.get("CODEX_MANAGED_BY_NPM"):
        return "codex"
    if environment.get("OPENCLAW_SESSION_ID") or environment.get("OPENCLAW_RUNTIME"):
        return "openclaw"
    if environment.get("CURSOR_TRACE_ID") or environment.get("CURSOR_AGENT"):
        return "cursor"
    return "unknown"


def check_executable(name: str, version_args: list[str] | None, runner: CommandRunner) -> dict[str, Any]:
    path = shutil.which(name)
    result = {
        "installed": bool(path),
        "path": path or "",
        "version": "",
        "ok": bool(path),
        "error": "",
    }
    if not path or not version_args:
        return result
    version_run = runner([name, *version_args], 5)
    result["ok"] = version_run["ok"]
    result["version"] = first_line(version_run["stdout"] or version_run["stderr"])
    if not version_run["ok"]:
        result["error"] = version_run["stderr"] or version_run["stdout"]
    return result


def resolve_bb_mode(requested_mode: str, openclaw_available: bool) -> str:
    normalized = (requested_mode or "auto").strip().lower()
    if normalized not in BB_MODES:
        raise SystemExit(f"invalid bb-browser mode: {requested_mode}")
    if normalized == "auto":
        return "standalone_extension"
    return normalized


def check_bb_browser(
    runner: CommandRunner,
    requested_mode: str,
    open_timeout: int,
    snapshot_timeout: int,
    host_runtime: str = "",
) -> dict[str, Any]:
    installed = check_executable("bb-browser", ["--version"], runner)
    openclaw_cli = runner(["bb-browser", "--help"], 5) if installed["installed"] else {"ok": False, "stdout": "", "stderr": ""}
    openclaw_available = "--openclaw" in f"{openclaw_cli.get('stdout', '')}\n{openclaw_cli.get('stderr', '')}"
    active_host_runtime = host_runtime or detect_host_runtime()
    resolved_mode = resolve_bb_mode(requested_mode, openclaw_available) if installed["installed"] else requested_mode
    result = {
        **installed,
        "open_ok": False,
        "snapshot_ok": False,
        "smoke_ok": False,
        "requested_mode": requested_mode,
        "resolved_mode": resolved_mode,
        "openclaw_flag_available": openclaw_available,
        "host_runtime": active_host_runtime,
        "mode_allowed": True,
        "smoke_error": "",
    }
    if not installed["installed"]:
        return result
    if resolved_mode == "openclaw" and active_host_runtime == "codex":
        result["mode_allowed"] = False
        result["smoke_error"] = "OpenClaw mode is not supported from Codex. Use standalone_extension, or run this skill inside OpenClaw instead."
        return result
    if resolved_mode == "disabled":
        result["smoke_error"] = "bb-browser disabled by configuration"
        return result
    if resolved_mode == "mcp":
        result["smoke_error"] = "mcp mode requires external MCP wiring; no local CLI smoke is attempted"
        return result

    bb_prefix = ["bb-browser"]
    if resolved_mode == "openclaw":
        bb_prefix.append("--openclaw")

    open_run = runner([*bb_prefix, "open", "about:blank", "--tab"], open_timeout)
    result["open_ok"] = open_run["ok"]
    if not open_run["ok"]:
        result["smoke_error"] = open_run["stderr"] or open_run["stdout"] or "bb-browser open failed"
        return result

    snapshot_run = runner([*bb_prefix, "snapshot", "-i"], snapshot_timeout)
    result["snapshot_ok"] = snapshot_run["ok"] and bool(snapshot_run["stdout"])
    result["smoke_ok"] = result["open_ok"] and result["snapshot_ok"]
    if not result["smoke_ok"]:
        result["smoke_error"] = snapshot_run["stderr"] or snapshot_run["stdout"] or "bb-browser snapshot failed"
    return result


def check_gog(runner: CommandRunner) -> dict[str, Any]:
    installed = check_executable("gog", ["--help"], runner)
    result = {
        **installed,
        "config_exists": False,
        "credentials_exists": False,
        "auth_preferred": "",
        "account": "",
        "configured": False,
        "status_raw": {},
    }
    if not installed["installed"]:
        return result

    status_run = runner(["gog", "auth", "status", "--plain"], 5)
    result["ok"] = status_run["ok"]
    if not status_run["ok"]:
        result["error"] = status_run["stderr"] or status_run["stdout"] or "gog auth status failed"
        return result

    parsed = parse_gog_status(status_run["stdout"])
    result["status_raw"] = parsed
    result["config_exists"] = parsed.get("config_exists", "").lower() == "true"
    result["credentials_exists"] = parsed.get("credentials_exists", "").lower() == "true"
    result["auth_preferred"] = parsed.get("auth_preferred", "")
    result["account"] = parsed.get("account", "")
    result["configured"] = result["config_exists"]
    return result


def derive_preflight_summary(checks: dict[str, Any]) -> dict[str, Any]:
    blockers: list[str] = []
    warnings: list[str] = []

    node_ready = checks["node"]["installed"] and checks["node"]["ok"]
    pnpm_ready = checks["pnpm"]["installed"] and checks["pnpm"]["ok"]
    bb_ready = checks["bb_browser"]["installed"] and checks["bb_browser"]["smoke_ok"]
    gog_installed = checks["gog"]["installed"]
    gog_configured = checks["gog"]["configured"]
    bb_mode = checks["bb_browser"].get("resolved_mode", "disabled")
    host_runtime = checks["bb_browser"].get("host_runtime", "unknown")
    mode_allowed = checks["bb_browser"].get("mode_allowed", True)

    if not node_ready:
        blockers.append("node_missing")
    if not pnpm_ready:
        warnings.append("pnpm_missing")
    if not mode_allowed:
        blockers.append("bb_browser_mode_not_supported")
    if not checks["bb_browser"]["installed"]:
        warnings.append("bb_browser_missing")
    elif not checks["bb_browser"]["smoke_ok"]:
        warnings.append("bb_browser_smoke_failed")
    if not gog_installed:
        warnings.append("gog_missing")
    elif not gog_configured:
        warnings.append("gog_unconfigured")

    if bb_mode == "mcp":
        warnings.append("bb_browser_mcp_requires_external_wiring")

    default_provider = "bb-browser" if bb_ready and bb_mode != "mcp" and mode_allowed else "dry-run"
    return {
        "generated_at": now_iso(),
        "host_runtime": host_runtime,
        "bb_browser_mode": bb_mode,
        "default_provider": default_provider,
        "ready_for_real_submit": node_ready and bb_ready and mode_allowed,
        "ready_for_verification": gog_installed and gog_configured,
        "blockers": blockers,
        "warnings": warnings,
    }


def run_preflight_checks(runner: CommandRunner | None = None, bb_mode: str = "auto", open_timeout: int = 10, snapshot_timeout: int = 8) -> dict[str, Any]:
    command_runner = runner or run_command
    host_runtime = detect_host_runtime()
    checks = {
        "node": check_executable("node", ["-v"], command_runner),
        "pnpm": check_executable("pnpm", ["-v"], command_runner),
        "bb_browser": check_bb_browser(
            command_runner,
            requested_mode=bb_mode,
            open_timeout=open_timeout,
            snapshot_timeout=snapshot_timeout,
            host_runtime=host_runtime,
        ),
        "gog": check_gog(command_runner),
    }
    summary = derive_preflight_summary(checks)
    return {
        "ok": len(summary["blockers"]) == 0,
        "checks": checks,
        **summary,
    }


def attach_to_manifest(manifest_path: Path, payload: dict[str, Any]) -> dict[str, Any]:
    manifest = load_json(manifest_path, {})
    manifest["preflight"] = payload
    manifest["updated_at"] = now_iso()
    save_json(manifest_path, manifest)
    return manifest


def main() -> int:
    parser = argparse.ArgumentParser(description="Check whether the local environment is ready for backlink-helper execution.")
    parser.add_argument("--manifest", default="")
    parser.add_argument("--out", default="")
    parser.add_argument("--bb-mode", default="auto", choices=sorted(BB_MODES))
    parser.add_argument("--open-timeout", type=int, default=10)
    parser.add_argument("--snapshot-timeout", type=int, default=8)
    args = parser.parse_args()

    payload = run_preflight_checks(bb_mode=args.bb_mode, open_timeout=args.open_timeout, snapshot_timeout=args.snapshot_timeout)
    if args.out:
        save_json(Path(args.out).expanduser().resolve(), payload)
    if args.manifest:
        manifest = attach_to_manifest(Path(args.manifest).expanduser().resolve(), payload)
        print(json.dumps({"ok": True, "preflight": payload, "manifest_path": str(Path(args.manifest).expanduser().resolve()), "manifest_status": manifest.get("status", "")}, ensure_ascii=False, indent=2))
        return 0
    print(json.dumps({"ok": True, "preflight": payload}, ensure_ascii=False, indent=2))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
