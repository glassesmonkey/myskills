#!/usr/bin/env python3
from __future__ import annotations

import argparse
import json
from urllib.parse import parse_qsl, urlencode, urlsplit, urlunsplit


def parse_extra(values: list[str]) -> dict[str, str]:
    extra: dict[str, str] = {}
    for item in values:
        if "=" not in item:
            raise SystemExit(f"invalid --set value: {item!r}; expected key=value")
        key, value = item.split("=", 1)
        extra[key.strip()] = value.strip()
    return extra


def main() -> int:
    parser = argparse.ArgumentParser(description="Build a tracked UTM URL for a backlink submission.")
    parser.add_argument("--base-url", required=True)
    parser.add_argument("--source", required=True)
    parser.add_argument("--medium", default="directory")
    parser.add_argument("--campaign", default="backlink")
    parser.add_argument("--content", default="")
    parser.add_argument("--term", default="")
    parser.add_argument("--set", action="append", default=[])
    parser.add_argument("--plain", action="store_true")
    args = parser.parse_args()

    parts = urlsplit(args.base_url.strip())
    query = dict(parse_qsl(parts.query, keep_blank_values=True))
    query.update(
        {
            "utm_source": args.source,
            "utm_medium": args.medium,
            "utm_campaign": args.campaign,
        }
    )
    if args.content:
        query["utm_content"] = args.content
    if args.term:
        query["utm_term"] = args.term
    query.update(parse_extra(args.set))

    built_url = urlunsplit((parts.scheme, parts.netloc, parts.path, urlencode(query, doseq=True), parts.fragment))
    if args.plain:
        print(built_url)
    else:
        print(json.dumps({"ok": True, "url": built_url, "query": query}, ensure_ascii=False, indent=2))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
