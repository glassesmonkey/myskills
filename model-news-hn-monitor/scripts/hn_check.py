#!/usr/bin/env python3
import argparse
import json
import re
import sys
import urllib.parse
import urllib.request


def normalize_text(value: str) -> str:
    value = (value or "").strip().lower()
    value = re.sub(r"[^a-z0-9]+", " ", value)
    return re.sub(r"\s+", " ", value).strip()


def normalize_url(url: str) -> str:
    url = (url or "").strip().lower()
    url = re.sub(r"#.*$", "", url)
    url = re.sub(r"/$", "", url)
    return url


def fetch_json(url: str):
    req = urllib.request.Request(url, headers={"User-Agent": "Mozilla/5.0"})
    with urllib.request.urlopen(req, timeout=20) as resp:
        return json.load(resp)


def search_url(url: str):
    q = urllib.parse.quote(url, safe="")
    api = f"https://hn.algolia.com/api/v1/search?tags=story&restrictSearchableAttributes=url&query={q}"
    return fetch_json(api).get("hits", [])


def search_title(title: str):
    q = urllib.parse.quote(title, safe="")
    api = f"https://hn.algolia.com/api/v1/search?tags=story&restrictSearchableAttributes=title&query={q}"
    return fetch_json(api).get("hits", [])


def summarize(hit):
    return {
        "objectID": hit.get("objectID"),
        "title": hit.get("title"),
        "url": hit.get("url"),
        "points": hit.get("points"),
        "num_comments": hit.get("num_comments"),
        "created_at": hit.get("created_at"),
    }


def main():
    p = argparse.ArgumentParser(description="Check existing Hacker News submissions via Algolia")
    p.add_argument("--url")
    p.add_argument("--title")
    args = p.parse_args()
    if not args.url and not args.title:
        raise SystemExit("Provide --url and/or --title")

    out = {
        "url_query": args.url,
        "title_query": args.title,
        "url_match_exists": False,
        "title_match_exists": False,
        "url_hits": [],
        "title_hits": [],
    }

    if args.url:
        url_hits = search_url(args.url)
        out["url_hits"] = [summarize(h) for h in url_hits[:10]]
        query_norm = normalize_url(args.url)
        out["url_match_exists"] = any(normalize_url((h.get("url") or "")) == query_norm for h in url_hits)

    if args.title:
        title_hits = search_title(args.title)
        out["title_hits"] = [summarize(h) for h in title_hits[:10]]
        query_norm = normalize_text(args.title)
        out["title_match_exists"] = any(normalize_text((h.get("title") or "")) == query_norm for h in title_hits)

    print(json.dumps(out, ensure_ascii=False, indent=2))


if __name__ == "__main__":
    main()
