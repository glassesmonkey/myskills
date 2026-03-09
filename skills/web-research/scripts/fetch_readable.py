#!/usr/bin/env python3
"""Fetch readable web content using Scrapling + html2text."""

from __future__ import annotations

import re
import sys
from pathlib import Path
from urllib.parse import urlparse

VENDOR_PYLIB = Path(__file__).resolve().parents[1] / "vendor" / "pylib"
if VENDOR_PYLIB.exists() and str(VENDOR_PYLIB) not in sys.path:
    sys.path.insert(0, str(VENDOR_PYLIB))

import html2text
from scrapling.fetchers import Fetcher

DEFAULT_MAX_CHARS = 30000


def validate_url(url: str) -> None:
    parsed = urlparse(url)
    if parsed.scheme not in {"http", "https"} or not parsed.netloc:
        raise ValueError(f"invalid url: {url}")


def build_converter() -> html2text.HTML2Text:
    h = html2text.HTML2Text()
    h.ignore_links = False
    h.ignore_images = False
    h.body_width = 0
    return h


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
            lambda m: f'<img{m.group(1)} src="{m.group(2)}"{m.group(3)}>',
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


def normalize_markdown(text: str) -> str:
    return re.sub(r"\n{3,}", "\n\n", text).strip()


def fetch_markdown(url: str, max_chars: int = DEFAULT_MAX_CHARS) -> tuple[str, str]:
    validate_url(url)

    fetcher = Fetcher()
    try:
        fetcher.configure(auto_match=False)
    except Exception:
        pass

    page = fetcher.get(url, headers={"Referer": "https://www.google.com/search?q=site"})
    if getattr(page, "status", 0) and int(page.status) >= 400:
        raise RuntimeError(f"http status {page.status} for {url}")

    h = build_converter()

    for selector in selectors_for(url):
        try:
            els = page.css(selector)
        except Exception:
            continue
        if not els:
            continue
        html_raw = fix_lazy_images(els[0].html_content)
        md = normalize_markdown(h.handle(html_raw))
        if len(md) > 300:
            return md[:max_chars], selector

    html_raw = fix_lazy_images(page.html_content)
    md = normalize_markdown(h.handle(html_raw))
    return md[:max_chars], "body(fallback)"


def main() -> int:
    if len(sys.argv) < 2:
        print("Usage: python3 fetch_readable.py <url> [max_chars]", file=sys.stderr)
        return 1

    url = sys.argv[1]
    max_chars = int(sys.argv[2]) if len(sys.argv) > 2 else DEFAULT_MAX_CHARS

    try:
        text, selector = fetch_markdown(url, max_chars)
    except Exception as exc:
        print(f"ERROR: {exc}", file=sys.stderr)
        return 2

    print(text)
    print(f"\n\n<!-- selector: {selector} -->", file=sys.stderr)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
