#!/usr/bin/env python3
from __future__ import annotations

import argparse
import json
import sys
from pathlib import Path
from typing import Any

from browser_runtime import resolve_browser_runtime

try:
    from playwright.sync_api import sync_playwright
except ImportError as error:  # pragma: no cover - import failure is surfaced at runtime
    raise SystemExit(f"Playwright is required: {error}")


def pick_page(browser: Any, url_prefix: str = "") -> Any:
    normalized_prefix = str(url_prefix or "").strip()
    fallback = None
    for context in browser.contexts:
        for page in context.pages:
            try:
                url = page.url
            except Exception:
                continue
            if normalized_prefix and url.startswith(normalized_prefix):
                return page
            if not fallback and not url.startswith("about:blank"):
                fallback = page
            if not fallback:
                fallback = page
    if fallback:
        return fallback
    raise RuntimeError("No page is available in the shared browser context")


def main() -> int:
    parser = argparse.ArgumentParser(description="Run deterministic Playwright actions against a shared CDP browser.")
    parser.add_argument("command", choices=["eval", "fill", "click", "screenshot"])
    parser.add_argument("--ws-url", default="")
    parser.add_argument("--cdp-url", default="")
    parser.add_argument("--url-prefix", default="")
    parser.add_argument("--selector", default="")
    parser.add_argument("--text", default="")
    parser.add_argument("--expr", default="")
    parser.add_argument("--path", default="")
    parser.add_argument("--timeout-ms", type=int, default=5000)
    args = parser.parse_args()

    runtime = resolve_browser_runtime(cdp_url=args.ws_url or args.cdp_url)
    ws_url = runtime.get("playwright_ws_url", "")
    if not ws_url:
        raise SystemExit(json.dumps({"ok": False, "error": runtime.get("error", "missing_playwright_ws_url")}, ensure_ascii=False))

    with sync_playwright() as playwright:
        browser = playwright.chromium.connect_over_cdp(ws_url)
        try:
            page = pick_page(browser, args.url_prefix)
            payload: dict[str, Any] = {
                "ok": True,
                "url": page.url,
                "command": args.command,
            }
            if args.command == "eval":
                if not args.expr:
                    raise SystemExit("--expr is required for eval")
                payload["result"] = page.evaluate(args.expr)
            elif args.command == "fill":
                if not args.selector:
                    raise SystemExit("--selector is required for fill")
                page.locator(args.selector).first.fill(args.text, timeout=args.timeout_ms)
                payload["filled"] = args.selector
                payload["value"] = page.locator(args.selector).first.input_value(timeout=args.timeout_ms)
            elif args.command == "click":
                if not args.selector:
                    raise SystemExit("--selector is required for click")
                page.locator(args.selector).first.click(timeout=args.timeout_ms)
                payload["clicked"] = args.selector
                payload["url"] = page.url
            elif args.command == "screenshot":
                if not args.path:
                    raise SystemExit("--path is required for screenshot")
                screenshot_path = Path(args.path).expanduser().resolve()
                screenshot_path.parent.mkdir(parents=True, exist_ok=True)
                page.screenshot(path=str(screenshot_path), full_page=True, timeout=args.timeout_ms)
                payload["path"] = str(screenshot_path)
            print(json.dumps(payload, ensure_ascii=False, indent=2))
            return 0
        finally:
            browser.close()


if __name__ == "__main__":
    raise SystemExit(main())
