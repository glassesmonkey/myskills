#!/usr/bin/env python3
from __future__ import annotations

import argparse
import json
import re
import subprocess
from html import unescape
from html.parser import HTMLParser
from pathlib import Path
from typing import Any
from urllib.parse import urljoin, urlsplit
from urllib.request import Request, urlopen

from common import domain_from_url, load_json, normalize_promoted_url, now_iso, save_json, unique_notes


ROLE_KEYWORDS = {
    "pricing": ["pricing", "plan", "plans", "price", "billing"],
    "features": ["feature", "features", "product", "how-it-works"],
    "about": ["about", "company", "team", "story"],
    "contact": ["contact", "support", "help", "get-in-touch"],
    "privacy": ["privacy", "gdpr"],
    "security": ["security", "trust", "compliance"],
    "docs": ["docs", "documentation", "guide", "manual"],
}

FIELD_ROLE_MAP = {
    "pricing_model": ["pricing"],
    "company_email": ["contact"],
    "trust_page": ["privacy", "security"],
    "about_company": ["about"],
    "feature_list": ["features", "docs"],
}


class PageParser(HTMLParser):
    def __init__(self, base_url: str):
        super().__init__(convert_charrefs=True)
        self.base_url = base_url
        self.title = ""
        self.og_title = ""
        self.description = ""
        self.og_description = ""
        self.canonical_url = ""
        self.headings: list[str] = []
        self.paragraphs: list[str] = []
        self.links: list[dict[str, str]] = []
        self.emails: list[str] = []
        self.social_links: list[str] = []
        self._capture_stack: list[dict[str, Any]] = []

    def handle_starttag(self, tag: str, attrs: list[tuple[str, str | None]]) -> None:
        attr_map = {key.lower(): value or "" for key, value in attrs}
        if tag in {"title", "h1", "h2", "p", "a"}:
            self._capture_stack.append({"tag": tag, "text": [], "href": attr_map.get("href", "")})
        if tag == "meta":
            name = attr_map.get("name", "").lower()
            prop = attr_map.get("property", "").lower()
            content = attr_map.get("content", "").strip()
            if name == "description" and content:
                self.description = content
            if prop == "og:title" and content:
                self.og_title = content
            if prop == "og:description" and content:
                self.og_description = content
        if tag == "link":
            rel = attr_map.get("rel", "").lower()
            href = attr_map.get("href", "").strip()
            if "canonical" in rel and href:
                self.canonical_url = urljoin(self.base_url, href)
        href = attr_map.get("href", "").strip()
        if href.startswith("mailto:"):
            self.emails.append(href.replace("mailto:", "", 1).strip())
        if href and any(domain in href for domain in ("twitter.com", "x.com", "linkedin.com", "github.com", "producthunt.com")):
            self.social_links.append(urljoin(self.base_url, href))

    def handle_data(self, data: str) -> None:
        if self._capture_stack:
            self._capture_stack[-1]["text"].append(data)

    def handle_endtag(self, tag: str) -> None:
        if not self._capture_stack or self._capture_stack[-1]["tag"] != tag:
            return
        item = self._capture_stack.pop()
        text = " ".join(item["text"]).strip()
        text = re.sub(r"\s+", " ", unescape(text))
        if not text:
            return
        if tag == "title":
            self.title = text
        elif tag in {"h1", "h2"}:
            self.headings.append(text)
        elif tag == "p":
            self.paragraphs.append(text)
        elif tag == "a":
            href = item["href"].strip()
            if href:
                self.links.append({"href": urljoin(self.base_url, href), "text": text})


def fetch_html(url: str, timeout: int) -> tuple[str, str]:
    try:
        request = Request(
            url,
            headers={
                "User-Agent": "Mozilla/5.0 (compatible; BacklinkHelper/1.0; +https://example.invalid)",
                "Accept": "text/html,application/xhtml+xml",
            },
        )
        with urlopen(request, timeout=timeout) as response:
            final_url = response.geturl()
            charset = response.headers.get_content_charset() or "utf-8"
            body = response.read().decode(charset, errors="replace")
        return final_url, body
    except Exception as first_error:
        for extra_args in ([], ["--proxy", "http://127.0.0.1:7890"]):
            result = subprocess.run(
                [
                    "curl",
                    "-LfsS",
                    "--max-time",
                    str(timeout),
                    *extra_args,
                    url,
                ],
                capture_output=True,
                text=True,
                check=False,
            )
            if result.returncode == 0 and result.stdout:
                return url, result.stdout
        raise first_error


def extract_page(url: str, timeout: int) -> dict[str, Any]:
    final_url, html = fetch_html(url, timeout)
    parser = PageParser(final_url)
    parser.feed(html)
    parser.close()

    emails = set(parser.emails)
    for match in re.findall(r"[A-Z0-9._%+-]+@[A-Z0-9.-]+\.[A-Z]{2,}", html, re.I):
        emails.add(match.lower())

    return {
        "url": final_url,
        "title": parser.og_title or parser.title,
        "description": parser.og_description or parser.description,
        "canonical_url": parser.canonical_url or final_url,
        "headings": unique_notes(parser.headings, limit=10),
        "paragraphs": unique_notes(parser.paragraphs, limit=8),
        "links": parser.links,
        "emails": sorted(emails),
        "social_links": unique_notes(parser.social_links, limit=12),
    }


def roles_from_needs(needs: list[str], follow_key_pages: bool) -> list[str]:
    roles: list[str] = []
    if follow_key_pages:
        roles.extend(["pricing", "features", "about", "contact", "privacy"])
    for need in needs:
        roles.extend(FIELD_ROLE_MAP.get(need, [need]))
    ordered: list[str] = []
    for role in roles:
        if role in ROLE_KEYWORDS and role not in ordered:
            ordered.append(role)
    return ordered


def discover_role_urls(home_page: dict[str, Any], roles: list[str], max_pages: int) -> dict[str, str]:
    base_domain = domain_from_url(home_page["url"])
    discovered: dict[str, str] = {}
    for link in home_page.get("links", []):
        href = link.get("href", "")
        if domain_from_url(href) != base_domain:
            continue
        haystack = f"{href} {link.get('text', '')}".lower()
        for role in roles:
            if role in discovered:
                continue
            if any(keyword in haystack for keyword in ROLE_KEYWORDS[role]):
                discovered[role] = href
        if len(discovered) >= max_pages:
            break
    return discovered


def choose_product_name(home_page: dict[str, Any]) -> str:
    for value in [home_page.get("title", ""), *(home_page.get("headings", []) or [])]:
        cleaned = str(value).strip()
        if cleaned:
            return cleaned
    return domain_from_url(home_page.get("url", ""))


def choose_short_description(home_page: dict[str, Any]) -> str:
    for value in [home_page.get("description", ""), *(home_page.get("paragraphs", []) or [])]:
        cleaned = str(value).strip()
        if cleaned:
            return cleaned[:280]
    return ""


def choose_medium_description(home_page: dict[str, Any], pages: dict[str, dict[str, Any]]) -> str:
    parts: list[str] = []
    for value in home_page.get("paragraphs", [])[:2]:
        if value:
            parts.append(value)
    for role in ("features", "about", "pricing"):
        for value in pages.get(role, {}).get("paragraphs", [])[:1]:
            if value:
                parts.append(value)
    joined = " ".join(unique_notes(parts, limit=4))
    return joined[:900]


def merge_values(existing: Any, fresh: Any) -> Any:
    if isinstance(existing, dict) and isinstance(fresh, dict):
        merged = dict(existing)
        for key, value in fresh.items():
            merged[key] = merge_values(existing.get(key), value) if key in existing else value
        return merged
    if isinstance(existing, list) and isinstance(fresh, list):
        return unique_notes([*existing, *fresh], limit=50)
    return fresh if fresh not in ("", None, [], {}) else existing


def compute_missing_fields(profile: dict[str, Any]) -> list[str]:
    missing = []
    if not profile.get("product_name"):
        missing.append("product_name")
    if not profile.get("short_description"):
        missing.append("short_description")
    if not profile.get("facts", {}).get("contact_emails"):
        missing.append("company_email")
    if not profile.get("facts", {}).get("pricing_url"):
        missing.append("pricing_model")
    if not profile.get("facts", {}).get("privacy_url"):
        missing.append("trust_page")
    return missing


def main() -> int:
    parser = argparse.ArgumentParser(description="Probe a promoted website and build a reusable material pack.")
    parser.add_argument("--url", required=True)
    parser.add_argument("--out", default="")
    parser.add_argument("--need", action="append", default=[])
    parser.add_argument("--max-pages", type=int, default=5)
    parser.add_argument("--timeout", type=int, default=20)
    parser.add_argument("--no-follow-key-pages", action="store_true")
    args = parser.parse_args()

    promoted_url = normalize_promoted_url(args.url)
    home_page = extract_page(promoted_url, args.timeout)
    roles = roles_from_needs(args.need, follow_key_pages=not args.no_follow_key_pages)
    role_urls = discover_role_urls(home_page, roles, args.max_pages)

    pages: dict[str, dict[str, Any]] = {}
    page_errors: dict[str, str] = {}
    for role, url in role_urls.items():
        try:
            pages[role] = extract_page(url, args.timeout)
        except Exception as exc:
            page_errors[role] = str(exc)

    contact_emails = sorted(
        {
            *home_page.get("emails", []),
            *pages.get("contact", {}).get("emails", []),
        }
    )
    social_links = unique_notes(
        [
            *home_page.get("social_links", []),
            *pages.get("about", {}).get("social_links", []),
        ],
        limit=12,
    )
    feature_hints = unique_notes(
        [
            *home_page.get("headings", []),
            *pages.get("features", {}).get("headings", []),
            *pages.get("features", {}).get("paragraphs", [])[:2],
        ],
        limit=12,
    )

    profile = {
        "profile_version": 1,
        "fetched_at": now_iso(),
        "requested_needs": unique_notes(args.need, limit=20),
        "promoted_url": promoted_url,
        "canonical_url": home_page.get("canonical_url") or promoted_url,
        "product_name": choose_product_name(home_page),
        "one_liner": choose_short_description(home_page)[:140],
        "short_description": choose_short_description(home_page),
        "medium_description": choose_medium_description(home_page, pages),
        "sources": unique_notes(
            [
                promoted_url,
                *(page.get("url", "") for page in pages.values()),
            ],
            limit=20,
        ),
        "pages": {
            "home": home_page,
            **pages,
        },
        "facts": {
            "contact_emails": contact_emails,
            "pricing_url": pages.get("pricing", {}).get("url", ""),
            "contact_url": pages.get("contact", {}).get("url", ""),
            "about_url": pages.get("about", {}).get("url", ""),
            "privacy_url": pages.get("privacy", {}).get("url", ""),
            "security_url": pages.get("security", {}).get("url", ""),
            "social_links": social_links,
        },
        "materials": {
            "feature_hints": feature_hints,
            "category_hints": unique_notes(home_page.get("headings", [])[:5], limit=8),
        },
        "page_errors": page_errors,
    }
    profile["missing_fields"] = compute_missing_fields(profile)

    if args.out:
        out_path = Path(args.out).expanduser().resolve()
        existing = load_json(out_path, {}) if out_path.exists() else {}
        merged = merge_values(existing, profile)
        merged["missing_fields"] = compute_missing_fields(merged)
        save_json(out_path, merged)
        print(json.dumps({"ok": True, "profile_path": str(out_path), "profile": merged}, ensure_ascii=False, indent=2))
        return 0

    print(json.dumps({"ok": True, "profile": profile}, ensure_ascii=False, indent=2))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
