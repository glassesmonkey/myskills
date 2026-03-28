#!/usr/bin/env python3
from __future__ import annotations

import argparse
import json
import os
import shutil
import subprocess
from pathlib import Path
from typing import Any, Callable

from browser_runtime import resolve_browser_runtime
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


def resolve_browser_use_binary() -> str:
    env_candidates = [
        os.environ.get("BACKLINK_BROWSER_USE_BIN", ""),
        os.environ.get("BROWSER_USE_BIN", ""),
    ]
    for candidate in env_candidates:
        value = str(candidate or "").strip()
        if value and Path(value).expanduser().exists():
            return str(Path(value).expanduser().resolve())

    discovered = shutil.which("browser-use")
    if discovered:
        return discovered

    home = Path.home()
    fallbacks = [
        home / ".browser-use-env" / "bin" / "browser-use",
        home / ".local" / "bin" / "browser-use",
        home / ".browser-use-env" / "Scripts" / "browser-use.exe",
    ]
    for candidate in fallbacks:
        if candidate.exists():
            return str(candidate.resolve())
    return ""


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
    version_run = runner([path, *version_args], 5)
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


def check_browser_runtime(cdp_url: str, timeout: int) -> dict[str, Any]:
    return resolve_browser_runtime(cdp_url=cdp_url, timeout=timeout)


def check_browser_use(runner: CommandRunner, runtime: dict[str, Any], state_timeout: int) -> dict[str, Any]:
    binary = resolve_browser_use_binary()
    result = {
        "installed": bool(binary),
        "path": binary,
        "version": "",
        "ok": bool(binary),
        "error": "",
        "runtime_configured": bool(runtime.get("configured", False)),
        "runtime_ok": bool(runtime.get("ok", False)),
        "state_ok": False,
        "smoke_ok": False,
        "smoke_error": "",
        "current_url": "",
    }
    if not binary:
        return result

    version_run = runner([binary, "--help"], 5)
    result["ok"] = version_run["ok"]
    result["version"] = first_line(version_run["stdout"] or version_run["stderr"])
    if not version_run["ok"]:
        result["error"] = version_run["stderr"] or version_run["stdout"]
        return result
    if not runtime.get("configured", False):
        result["smoke_error"] = "No shared CDP URL configured. Set BACKLINK_BROWSER_CDP_URL, BROWSER_USE_CDP_URL, CHROME_CDP_URL, or pass --cdp-url."
        return result
    if not runtime.get("ok", False):
        result["smoke_error"] = runtime.get("error", "CDP runtime probe failed")
        return result

    prefix = [binary, "--cdp-url", runtime.get("cdp_url", "")]
    state_run = runner([*prefix, "state"], state_timeout)
    result["state_ok"] = state_run["ok"] and bool((state_run["stdout"] or "").strip())
    if not result["state_ok"]:
        result["smoke_error"] = state_run["stderr"] or state_run["stdout"] or "browser-use state failed"
        return result

    url_run = runner([*prefix, "eval", "location.href"], 5)
    result["current_url"] = first_line((url_run["stdout"] or "").replace("result:", "").strip()) if url_run["ok"] else ""
    result["smoke_ok"] = True
    return result


def check_bb_browser(
    runner: CommandRunner,
    requested_mode: str,
    snapshot_timeout: int,
    host_runtime: str = "",
) -> dict[str, Any]:
    installed = check_executable("bb-browser", ["--version"], runner)
    bb_binary = installed.get("path") or "bb-browser"
    openclaw_cli = runner([bb_binary, "--help"], 5) if installed["installed"] else {"ok": False, "stdout": "", "stderr": ""}
    openclaw_available = "--openclaw" in f"{openclaw_cli.get('stdout', '')}\n{openclaw_cli.get('stderr', '')}"
    active_host_runtime = host_runtime or detect_host_runtime()
    resolved_mode = resolve_bb_mode(requested_mode, openclaw_available) if installed["installed"] else requested_mode
    result = {
        **installed,
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

    bb_prefix = [bb_binary]
    if resolved_mode == "openclaw":
        bb_prefix.append("--openclaw")

    snapshot_run = runner([*bb_prefix, "snapshot", "-i"], snapshot_timeout)
    result["snapshot_ok"] = snapshot_run["ok"] and bool(snapshot_run["stdout"])
    result["smoke_ok"] = result["snapshot_ok"]
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

    status_run = runner([installed.get("path") or "gog", "auth", "status", "--plain"], 5)
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

    browser_runtime = checks.get("browser_runtime", {}) or {}
    browser_use = checks.get("browser_use", {}) or {}
    browser_runtime_configured = bool(browser_runtime.get("configured", False))
    browser_runtime_ok = bool(browser_runtime.get("ok", False))
    browser_use_ready = browser_runtime_configured and browser_runtime_ok and browser_use.get("installed", False) and browser_use.get("smoke_ok", False)

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

    if browser_runtime_configured:
        if not browser_runtime_ok:
            warnings.append("browser_cdp_probe_failed")
        if not browser_use.get("installed", False):
            warnings.append("browser_use_missing")
        elif not browser_use.get("smoke_ok", False):
            warnings.append("browser_use_smoke_failed")
    elif not bb_ready:
        warnings.append("browser_cdp_unconfigured")

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

    if browser_use_ready:
        default_provider = "browser-use-cli"
    elif bb_ready and bb_mode != "mcp" and mode_allowed:
        default_provider = "bb-browser"
    else:
        default_provider = "dry-run"

    return {
        "generated_at": now_iso(),
        "host_runtime": host_runtime,
        "bb_browser_mode": bb_mode,
        "default_provider": default_provider,
        "ready_for_real_submit": node_ready and (browser_use_ready or (bb_ready and mode_allowed)),
        "ready_for_verification": gog_installed and gog_configured,
        "blockers": blockers,
        "warnings": warnings,
        "browser_runtime": browser_runtime,
    }


def run_preflight_checks(
    runner: CommandRunner | None = None,
    bb_mode: str = "auto",
    snapshot_timeout: int = 8,
    browser_state_timeout: int = 8,
    cdp_url: str = "",
    cdp_timeout: int = 5,
) -> dict[str, Any]:
    command_runner = runner or run_command
    host_runtime = detect_host_runtime()
    browser_runtime = check_browser_runtime(cdp_url=cdp_url, timeout=cdp_timeout)
    checks = {
        "node": check_executable("node", ["-v"], command_runner),
        "pnpm": check_executable("pnpm", ["-v"], command_runner),
        "browser_runtime": browser_runtime,
        "browser_use": check_browser_use(command_runner, browser_runtime, browser_state_timeout),
        "bb_browser": check_bb_browser(
            command_runner,
            requested_mode=bb_mode,
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
    parser.add_argument("--snapshot-timeout", type=int, default=8)
    parser.add_argument("--browser-state-timeout", type=int, default=8)
    parser.add_argument("--cdp-url", default="")
    parser.add_argument("--cdp-timeout", type=int, default=5)
    args = parser.parse_args()

    payload = run_preflight_checks(
        bb_mode=args.bb_mode,
        snapshot_timeout=args.snapshot_timeout,
        browser_state_timeout=args.browser_state_timeout,
        cdp_url=args.cdp_url,
        cdp_timeout=args.cdp_timeout,
    )
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
