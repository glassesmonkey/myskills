#!/usr/bin/env python3
"""Read a webpage via Jina Reader first, then fall back to Scrapling + html2text."""

from __future__ import annotations

import argparse
import re
import subprocess
import sys
from pathlib import Path
from typing import Callable
from urllib.parse import quote, urlparse

sys.dont_write_bytecode = True

SCRIPT_DIR = Path(__file__).resolve().parent
if str(SCRIPT_DIR) not in sys.path:
    sys.path.insert(0, str(SCRIPT_DIR))

from runtime_check import ensure_fallback_environment, ensure_jina_environment

DEFAULT_MAX_CHARS = 30000
DEFAULT_TIMEOUT_SECONDS = 20
ERROR_PATTERNS = (
    "error",
    "rate limit",
    "too many requests",
    "access denied",
    "forbidden",
    "captcha",
)


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser()
    parser.add_argument("url", help="Public http/https URL to read")
    parser.add_argument(
        "--mode",
        choices=("auto", "jina", "scrapling"),
        default="auto",
        help="Route selection. Default: auto.",
    )
    parser.add_argument(
        "--max-chars",
        type=int,
        default=DEFAULT_MAX_CHARS,
        help="Maximum number of characters to print.",
    )
    parser.add_argument(
        "--timeout",
        type=int,
        default=DEFAULT_TIMEOUT_SECONDS,
        help="Per-request timeout in seconds.",
    )
    return parser.parse_args()


def validate_url(url: str) -> None:
    parsed = urlparse(url)
    if parsed.scheme not in {"http", "https"} or not parsed.netloc:
        raise ValueError(f"invalid url: {url}")


def normalize_markdown(text: str) -> str:
    return re.sub(r"\n{3,}", "\n\n", text).strip()


def looks_usable(text: str, *, min_chars: int) -> bool:
    if len(text.strip()) < min_chars:
        return False
    lowered = text.lower()
    return not any(pattern in lowered for pattern in ERROR_PATTERNS)


def build_jina_url(url: str) -> str:
    return f"https://r.jina.ai/{quote(url, safe=':/?&=#%')}"


def read_via_jina(url: str, timeout: int, max_chars: int) -> str:
    ensure_jina_environment()
    command = [
        "curl",
        "-fsSL",
        "--max-time",
        str(timeout),
        "-H",
        "Accept: text/markdown",
        build_jina_url(url),
    ]
    result = subprocess.run(command, capture_output=True, text=True, check=False)
    if result.returncode != 0:
        stderr = result.stderr.strip() or f"curl exited with code {result.returncode}"
        raise RuntimeError(stderr)

    text = normalize_markdown(result.stdout)
    if not looks_usable(text, min_chars=200):
        raise RuntimeError("Jina returned empty or unusable content.")
    return text[:max_chars]


def build_converter():
    import html2text

    converter = html2text.HTML2Text()
    converter.ignore_links = False
    converter.ignore_images = False
    converter.body_width = 0
    return converter


def fix_lazy_images(html_raw: str) -> str:
    patterns = [
        r'<img([^>]*?)\sdata-src="([^"]+)"([^>]*?)>',
        r'<img([^>]*?)\sdata-original="([^"]+)"([^>]*?)>',
        r'<img([^>]*?)\sdata-original-src="([^"]+)"([^>]*?)>',
        r'<img([^>]*?)\sdata-actualsrc="([^"]+)"([^>]*?)>',
    ]
    for pattern in patterns:
        html_raw = re.sub(
            pattern,
            lambda match: (
                f'<img{match.group(1)} src="{match.group(2)}"{match.group(3)}>'
            ),
            html_raw,
        )
    return html_raw


def selectors_for(url: str) -> list[str]:
    if "mp.weixin.qq.com" in url:
        return ["div#js_content", "div.rich_media_content"]
    return [
        "article",
        "main",
        ".markdown-body",
        ".post-content",
        ".entry-content",
        ".article-body",
        "[class*='article']",
        "[class*='content']",
        "[class*='body']",
    ]


def read_via_scrapling(url: str, timeout: int, max_chars: int) -> str:
    ensure_fallback_environment()

    from scrapling.parser import Selector

    command = [
        "curl",
        "-fsSL",
        "--max-time",
        str(timeout),
        "-A",
        (
            "Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) "
            "AppleWebKit/537.36 (KHTML, like Gecko) "
            "Chrome/133.0.0.0 Safari/537.36"
        ),
        url,
    ]
    result = subprocess.run(command, capture_output=True, text=True, check=False)
    if result.returncode != 0:
        stderr = result.stderr.strip() or f"curl exited with code {result.returncode}"
        raise RuntimeError(stderr)

    html = result.stdout

    page = Selector(html)

    converter = build_converter()
    for selector in selectors_for(url):
        try:
            elements = page.css(selector)
        except Exception:
            continue
        if not elements:
            continue

        html_raw = fix_lazy_images(elements[0].html_content)
        markdown = normalize_markdown(converter.handle(html_raw))
        if len(markdown) >= 200:
            return markdown[:max_chars]

    markdown = normalize_markdown(converter.handle(fix_lazy_images(html)))
    if not looks_usable(markdown, min_chars=80):
        raise RuntimeError("Scrapling fallback did not extract usable content.")
    return markdown[:max_chars]


def main() -> int:
    args = parse_args()

    try:
        validate_url(args.url)
    except ValueError as exc:
        print(f"ERROR: {exc}", file=sys.stderr)
        return 1

    errors: list[str] = []

    routes: list[tuple[str, Callable[[str, int, int], str]]]
    if args.mode == "jina":
        routes = [("jina", read_via_jina)]
    elif args.mode == "scrapling":
        routes = [("scrapling", read_via_scrapling)]
    else:
        routes = [("jina", read_via_jina), ("scrapling", read_via_scrapling)]

    for route_name, handler in routes:
        try:
            content = handler(args.url, args.timeout, args.max_chars)
        except Exception as exc:
            errors.append(f"{route_name}: {exc}")
            continue

        print(content)
        print(f"\n<!-- route: {route_name} -->", file=sys.stderr)
        return 0

    for error in errors:
        print(f"ERROR: {error}", file=sys.stderr)
    return 2


if __name__ == "__main__":
    raise SystemExit(main())
