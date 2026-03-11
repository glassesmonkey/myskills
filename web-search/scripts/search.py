#!/usr/bin/env python3
"""
Search the web with Tavily first, then DuckDuckGo.
"""

from __future__ import annotations

import argparse
import contextlib
import io
import json
import os
import sys
import urllib.error
import urllib.request
from typing import Any


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(
        description="Search the web with Tavily first and DuckDuckGo as fallback."
    )
    parser.add_argument("query", help="Search query")
    parser.add_argument(
        "--max-results",
        type=int,
        default=5,
        help="Maximum number of results to return",
    )
    parser.add_argument(
        "--topic",
        choices=("general", "news"),
        default="general",
        help="Search topic for Tavily",
    )
    return parser.parse_args()


def tavily_search(query: str, max_results: int, topic: str) -> dict[str, Any]:
    api_key = os.environ.get("TAVILY_API_KEY")
    if not api_key:
        raise RuntimeError("TAVILY_API_KEY is not configured")

    payload = json.dumps(
        {
            "api_key": api_key,
            "query": query,
            "max_results": max_results,
            "topic": topic,
            "search_depth": "advanced",
            "include_answer": False,
            "include_images": False,
            "include_raw_content": False,
        }
    ).encode("utf-8")
    request = urllib.request.Request(
        "https://api.tavily.com/search",
        data=payload,
        headers={"Content-Type": "application/json"},
        method="POST",
    )
    try:
        with urllib.request.urlopen(request, timeout=20) as response:
            data = json.load(response)
    except urllib.error.HTTPError as exc:
        detail = exc.read().decode("utf-8", errors="replace")
        raise RuntimeError(f"Tavily HTTP {exc.code}: {detail}") from exc
    except urllib.error.URLError as exc:
        raise RuntimeError(f"Tavily request failed: {exc.reason}") from exc

    results = [
        {
            "title": item.get("title", ""),
            "url": item.get("url", ""),
            "snippet": item.get("content", ""),
            "score": item.get("score"),
        }
        for item in data.get("results", [])
    ]
    return {
        "provider": "tavily",
        "query": query,
        "results": results,
    }


def duckduckgo_search(query: str, max_results: int) -> dict[str, Any]:
    try:
        from duckduckgo_search import DDGS
    except ImportError as exc:
        raise RuntimeError(
            "duckduckgo-search is not installed. Run: python3 -m pip install duckduckgo-search"
        ) from exc

    results = []
    # The package currently prints a rename warning to stderr on normal use.
    with contextlib.redirect_stderr(io.StringIO()):
        with DDGS() as ddgs:
            for item in ddgs.text(query, max_results=max_results):
                results.append(
                    {
                        "title": item.get("title", ""),
                        "url": item.get("href", ""),
                        "snippet": item.get("body", ""),
                    }
                )

    return {
        "provider": "duckduckgo",
        "query": query,
        "results": results,
    }


def main() -> int:
    args = parse_args()

    try:
        payload = tavily_search(args.query, args.max_results, args.topic)
    except RuntimeError as tavily_error:
        print(
            f"[web-search] Tavily unavailable, falling back to DuckDuckGo: {tavily_error}",
            file=sys.stderr,
        )
        try:
            payload = duckduckgo_search(args.query, args.max_results)
        except RuntimeError as ddg_error:
            print(f"[web-search] DuckDuckGo fallback failed: {ddg_error}", file=sys.stderr)
            return 1

    json.dump(payload, sys.stdout, ensure_ascii=False, indent=2)
    sys.stdout.write("\n")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
