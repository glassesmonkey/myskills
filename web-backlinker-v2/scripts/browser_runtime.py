#!/usr/bin/env python3
from __future__ import annotations

import argparse
import json
import os
from pathlib import Path
from typing import Any, Callable
from urllib.error import URLError, HTTPError
from urllib.parse import urlparse
from urllib.request import urlopen

from common import save_json


ENV_KEYS = [
    "BACKLINK_BROWSER_CDP_URL",
    "BROWSER_USE_CDP_URL",
    "CHROME_CDP_URL",
]


JsonFetcher = Callable[[str, int], dict[str, Any]]


def pick_cdp_url(explicit: str = "", env: dict[str, str] | None = None) -> tuple[str, str]:
    raw = str(explicit or "").strip()
    if raw:
        return normalize_cdp_url(raw), "arg"
    environment = env or os.environ
    for key in ENV_KEYS:
        value = str(environment.get(key, "")).strip()
        if value:
            return normalize_cdp_url(value), f"env:{key}"
    return "", ""


def normalize_cdp_url(raw: str) -> str:
    value = str(raw or "").strip()
    if not value:
        return ""
    if value.startswith(("http://", "https://", "ws://", "wss://")):
        return value.rstrip("/")
    if "://" not in value and ":" in value:
        return f"http://{value}".rstrip("/")
    return value.rstrip("/")


def version_url_for(cdp_url: str) -> tuple[str, str]:
    normalized = normalize_cdp_url(cdp_url)
    if normalized.endswith("/json/version"):
        return normalized, normalized[: -len("/json/version")]
    return f"{normalized}/json/version", normalized


def fetch_json_version(version_url: str, timeout: int = 5) -> dict[str, Any]:
    with urlopen(version_url, timeout=timeout) as response:
        payload = response.read().decode("utf-8", "replace")
    return json.loads(payload)


def resolve_browser_runtime(
    cdp_url: str = "",
    env: dict[str, str] | None = None,
    timeout: int = 5,
    fetcher: JsonFetcher | None = None,
) -> dict[str, Any]:
    normalized, source = pick_cdp_url(cdp_url, env)
    runtime = {
        "configured": bool(normalized),
        "source": source,
        "cdp_url": normalized,
        "playwright_ws_url": "",
        "version_url": "",
        "transport": "",
        "ok": False,
        "error": "",
        "browser": "",
        "protocol_version": "",
        "user_agent": "",
        "host": "",
    }
    if not normalized:
        return runtime

    parsed = urlparse(normalized)
    runtime["host"] = parsed.hostname or ""
    runtime["transport"] = parsed.scheme

    if parsed.scheme in {"ws", "wss"}:
        runtime["playwright_ws_url"] = normalized
        runtime["ok"] = True
        return runtime

    if parsed.scheme not in {"http", "https"}:
        runtime["error"] = f"unsupported_cdp_scheme:{parsed.scheme or 'missing'}"
        return runtime

    version_url, base_url = version_url_for(normalized)
    runtime["version_url"] = version_url
    runtime["cdp_url"] = base_url
    loader = fetcher or fetch_json_version
    try:
        payload = loader(version_url, timeout)
        runtime["playwright_ws_url"] = str(payload.get("webSocketDebuggerUrl", "")).strip()
        runtime["browser"] = str(payload.get("Browser", "")).strip()
        runtime["protocol_version"] = str(payload.get("Protocol-Version", "")).strip()
        runtime["user_agent"] = str(payload.get("User-Agent", "")).strip()
        runtime["ok"] = bool(runtime["playwright_ws_url"])
        if not runtime["ok"]:
            runtime["error"] = "missing_websocket_debugger_url"
    except (HTTPError, URLError, TimeoutError, OSError, json.JSONDecodeError) as error:
        runtime["error"] = str(error)
    return runtime


def main() -> int:
    parser = argparse.ArgumentParser(description="Resolve a shared Chrome CDP endpoint for browser-use CLI and Playwright.")
    parser.add_argument("--cdp-url", default="")
    parser.add_argument("--timeout", type=int, default=5)
    parser.add_argument("--out", default="")
    args = parser.parse_args()

    runtime = resolve_browser_runtime(cdp_url=args.cdp_url, timeout=args.timeout)
    payload = {"ok": runtime["ok"], "runtime": runtime}
    if args.out:
        save_json(Path(args.out).expanduser().resolve(), payload)
    print(json.dumps(payload, ensure_ascii=False, indent=2))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
