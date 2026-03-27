#!/usr/bin/env python3
from __future__ import annotations

import argparse
import json
import re
import shutil
import subprocess
from typing import Any

from common import unique_notes


VERIFY_WORDS = ("verify", "verification", "confirm", "activate", "magic", "signin", "sign-in", "login", "auth", "code")


def ensure_gog_installed() -> None:
    if shutil.which("gog"):
        return
    raise SystemExit("gog is not installed or not on PATH")


def run_command(argv: list[str]) -> subprocess.CompletedProcess[str]:
    return subprocess.run(argv, capture_output=True, text=True, check=False)


def gog_status() -> dict[str, str]:
    result = run_command(["gog", "auth", "status", "--plain"])
    if result.returncode != 0:
        raise SystemExit(result.stderr.strip() or result.stdout.strip() or "failed to run `gog auth status`")
    data: dict[str, str] = {}
    for line in result.stdout.splitlines():
        if "\t" not in line:
            continue
        key, value = line.split("\t", 1)
        data[key.strip()] = value.strip()
    return data


def ensure_gog_configured() -> dict[str, str]:
    status = gog_status()
    if status.get("config_exists", "").lower() != "true":
        raise SystemExit("gog is installed but not configured; run `gog login <email>` first")
    return status


def run_gog_json(args: list[str]) -> Any:
    result = run_command(["gog", *args, "-j", "--results-only"])
    if result.returncode != 0:
        raise SystemExit(result.stderr.strip() or result.stdout.strip() or f"gog command failed: {' '.join(args)}")
    stdout = result.stdout.strip()
    if not stdout:
        return []
    return json.loads(stdout)


def build_query(args: argparse.Namespace) -> str:
    parts: list[str] = []
    if args.from_address:
        parts.append(f"from:({args.from_address})")
    if args.subject:
        parts.append(f"subject:({args.subject})")
    if args.newer_than:
        parts.append(f"newer_than:{args.newer_than}")
    parts.extend(args.query)
    query = " ".join(part.strip() for part in parts if part.strip())
    if not query:
        raise SystemExit("provide a Gmail query or use --from-address / --subject / --newer-than")
    return query


def walk_strings(value: Any) -> list[str]:
    if value is None:
        return []
    if isinstance(value, str):
        return [value]
    if isinstance(value, dict):
        strings: list[str] = []
        for item in value.values():
            strings.extend(walk_strings(item))
        return strings
    if isinstance(value, list):
        strings: list[str] = []
        for item in value:
            strings.extend(walk_strings(item))
        return strings
    return []


def collect_thread_ids(value: Any) -> list[str]:
    ids: list[str] = []
    if isinstance(value, dict):
        candidate = value.get("threadId") or value.get("id")
        if isinstance(candidate, str) and candidate:
            ids.append(candidate)
        for item in value.values():
            ids.extend(collect_thread_ids(item))
    elif isinstance(value, list):
        for item in value:
            ids.extend(collect_thread_ids(item))
    return unique_notes(ids, limit=50)


def extract_urls(strings: list[str]) -> list[str]:
    urls: list[str] = []
    for value in strings:
        for match in re.findall(r"https?://[^\s<>'\"()]+", value):
            cleaned = match.rstrip(".,;)")
            urls.append(cleaned)
    return unique_notes(urls, limit=200)


def extract_codes(strings: list[str]) -> list[str]:
    codes: list[str] = []
    for value in strings:
        for match in re.findall(r"\b\d{4,8}\b", value):
            codes.append(match)
        for match in re.findall(r"\b[A-Z0-9]{6,8}\b", value):
            if any(ch.isalpha() for ch in match):
                codes.append(match)
    return unique_notes(codes, limit=50)


def score_link(url: str) -> int:
    lowered = url.lower()
    score = 0
    for word in VERIFY_WORDS:
        if word in lowered:
            score += 10
    if "unsubscribe" in lowered:
        score -= 50
    return score


def main() -> int:
    parser = argparse.ArgumentParser(description="Search Gmail through gog and extract verification links or codes.")
    sub = parser.add_subparsers(dest="command", required=True)

    status = sub.add_parser("status")

    for name in ("search", "extract"):
        command = sub.add_parser(name)
        command.add_argument("query", nargs="*")
        command.add_argument("--account", default="")
        command.add_argument("--from-address", default="")
        command.add_argument("--subject", default="")
        command.add_argument("--newer-than", default="2d")
        command.add_argument("--max-results", type=int, default=5)

    args = parser.parse_args()
    ensure_gog_installed()

    if args.command == "status":
        status_info = gog_status()
        configured = status_info.get("config_exists", "").lower() == "true"
        print(json.dumps({"ok": True, "configured": configured, "status": status_info}, ensure_ascii=False, indent=2))
        return 0

    ensure_gog_configured()
    query = build_query(args)
    account_args = ["--account", args.account] if args.account else []
    search_result = run_gog_json(["gmail", "search", *account_args, "--max", str(args.max_results), query])
    thread_ids = collect_thread_ids(search_result)

    if args.command == "search":
        print(json.dumps({"ok": True, "query": query, "thread_ids": thread_ids, "results": search_result}, ensure_ascii=False, indent=2))
        return 0

    inspected_threads = []
    all_urls: list[str] = []
    all_codes: list[str] = []
    for thread_id in thread_ids[: args.max_results]:
        thread = run_gog_json(["gmail", "thread", "get", *account_args, "--full", thread_id])
        strings = walk_strings(thread)
        urls = extract_urls(strings)
        codes = extract_codes(strings)
        inspected_threads.append(
            {
                "thread_id": thread_id,
                "top_link": max(urls, key=score_link) if urls else "",
                "links": urls[:10],
                "codes": codes[:10],
            }
        )
        all_urls.extend(urls)
        all_codes.extend(codes)

    unique_urls = unique_notes(all_urls, limit=200)
    unique_codes = unique_notes(all_codes, limit=50)
    best_link = max(unique_urls, key=score_link) if unique_urls else ""
    best_code = unique_codes[0] if unique_codes else ""
    print(
        json.dumps(
            {
                "ok": True,
                "query": query,
                "thread_ids": thread_ids,
                "best_link": best_link,
                "best_code": best_code,
                "links": unique_urls[:20],
                "codes": unique_codes[:20],
                "threads": inspected_threads,
            },
            ensure_ascii=False,
            indent=2,
        )
    )
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
