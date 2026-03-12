#!/usr/bin/env python3
"""
Search the web with Exa first, then Tavily, then DuckDuckGo.
"""

from __future__ import annotations

import argparse
import contextlib
import io
import json
import os
import subprocess
import sys
from typing import Any, Callable


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(
        description="Search the web with Exa first, Tavily second, and DuckDuckGo as fallback."
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
    parser.add_argument(
        "--mode",
        choices=("standard", "research"),
        default="standard",
        help="Use standard fallback mode or collect all providers for research.",
    )
    return parser.parse_args()


def run_curl_json(command: list[str], provider_name: str) -> dict[str, Any]:
    try:
        completed = subprocess.run(
            command,
            check=True,
            capture_output=True,
            text=True,
        )
    except FileNotFoundError as exc:
        raise RuntimeError("curl is not installed or not available in PATH") from exc
    except subprocess.CalledProcessError as exc:
        detail = exc.stderr.strip() or exc.stdout.strip() or "unknown curl error"
        raise RuntimeError(f"{provider_name} request failed: {detail}") from exc

    try:
        return json.loads(completed.stdout)
    except json.JSONDecodeError as exc:
        raise RuntimeError(f"{provider_name} returned invalid JSON") from exc


def pick_snippet(*values: Any) -> str:
    for value in values:
        if isinstance(value, list):
            parts = [str(item).strip() for item in value if str(item).strip()]
            if parts:
                return "\n".join(parts)
        elif isinstance(value, str) and value.strip():
            return value.strip()
    return ""


def exa_search(query: str, max_results: int) -> dict[str, Any]:
    api_key = os.environ.get("EXA_API_KEY")
    if not api_key:
        raise RuntimeError("EXA_API_KEY is not configured")

    payload = json.dumps(
        {
            "query": query,
            "type": "auto",
            "numResults": max_results,
            "contents": {
                "highlights": {
                    "maxCharacters": 4000,
                }
            },
        }
    )

    command = [
        "curl",
        "--silent",
        "--show-error",
        "--fail-with-body",
        "--max-time",
        "20",
        "--request",
        "POST",
        "--url",
        "https://api.exa.ai/search",
        "--header",
        "accept: application/json",
        "--header",
        "content-type: application/json",
        "--header",
        f"x-api-key: {api_key}",
        "--data",
        payload,
    ]

    data = run_curl_json(command, "Exa")
    results = [
        {
            "title": item.get("title", ""),
            "url": item.get("url", ""),
            "snippet": pick_snippet(
                item.get("highlights"),
                item.get("text"),
                item.get("summary"),
            ),
            "published_date": item.get("publishedDate"),
            "score": item.get("score"),
        }
        for item in data.get("results", [])
    ]
    return {
        "provider": "exa",
        "query": query,
        "results": results,
    }


def tavily_search(query: str, max_results: int, topic: str) -> dict[str, Any]:
    api_key = os.environ.get("TAVILY_API_KEY")
    if not api_key:
        raise RuntimeError("TAVILY_API_KEY is not configured")

    payload = json.dumps(
        {
            "query": query,
            "max_results": max_results,
            "topic": topic,
            "search_depth": "advanced",
            "include_answer": False,
            "include_images": False,
            "include_raw_content": False,
        }
    )

    command = [
        "curl",
        "--silent",
        "--show-error",
        "--fail-with-body",
        "--max-time",
        "20",
        "-X",
        "POST",
        "https://api.tavily.com/search",
        "-H",
        "Content-Type: application/json",
        "-H",
        f"Authorization: Bearer {api_key}",
        "-d",
        payload,
    ]

    data = run_curl_json(command, "Tavily")

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


def run_standard_search(
    query: str,
    max_results: int,
    topic: str,
) -> dict[str, Any]:
    providers: list[tuple[str, Callable[[], dict[str, Any]]]] = [
        ("exa", lambda: exa_search(query, max_results)),
        ("tavily", lambda: tavily_search(query, max_results, topic)),
        ("duckduckgo", lambda: duckduckgo_search(query, max_results)),
    ]

    last_error: RuntimeError | None = None
    for provider_name, provider_search in providers:
        try:
            payload = provider_search()
            payload["mode"] = "standard"
            return payload
        except RuntimeError as error:
            last_error = error
            print(
                f"[web-search] {provider_name} unavailable, trying next provider: {error}",
                file=sys.stderr,
            )

    if last_error is None:
        raise RuntimeError("No search provider was attempted")
    raise last_error


def run_research_search(
    query: str,
    max_results: int,
    topic: str,
) -> dict[str, Any]:
    providers: list[tuple[str, Callable[[], dict[str, Any]]]] = [
        ("exa", lambda: exa_search(query, max_results)),
        ("tavily", lambda: tavily_search(query, max_results, topic)),
        ("duckduckgo", lambda: duckduckgo_search(query, max_results)),
    ]

    collected_results: list[dict[str, Any]] = []
    errors: list[dict[str, str]] = []

    for provider_name, provider_search in providers:
        try:
            collected_results.append(provider_search())
        except RuntimeError as error:
            errors.append(
                {
                    "provider": provider_name,
                    "error": str(error),
                }
            )
            print(
                f"[web-search] {provider_name} unavailable during research collection: {error}",
                file=sys.stderr,
            )

    if not collected_results:
        error_messages = ", ".join(item["error"] for item in errors) or "unknown error"
        raise RuntimeError(f"All providers failed: {error_messages}")

    return {
        "mode": "research",
        "query": query,
        "providers": collected_results,
        "errors": errors,
    }


def main() -> int:
    args = parse_args()

    try:
        if args.mode == "research":
            payload = run_research_search(args.query, args.max_results, args.topic)
        else:
            payload = run_standard_search(args.query, args.max_results, args.topic)
    except RuntimeError as search_error:
        print(f"[web-search] Search failed: {search_error}", file=sys.stderr)
        return 1

    json.dump(payload, sys.stdout, ensure_ascii=False, indent=2)
    sys.stdout.write("\n")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
