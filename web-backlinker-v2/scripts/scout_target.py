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
from urllib.parse import urljoin
from urllib.request import Request, urlopen

from common import domain_from_url, normalize_url, now_iso, save_json, unique_notes


SITE_TYPE_RULES = {
    "directory": ["submit tool", "submit your tool", "add listing", "add your product", "list your product", "submit startup"],
    "launch_platform": ["launch", "product of the day", "ship", "submit startup"],
    "community": ["community", "showcase", "introduce yourself"],
    "forum": ["forum", "reply", "new topic", "discussion"],
    "article_platform": ["write", "publish story", "editor", "draft"],
}

SUBMIT_HINTS = ("submit", "add", "list", "suggest", "contribute", "launch", "ship")
HARD_ANTI_BOT = {
    "cloudflare": ["cloudflare", "just a moment"],
    "turnstile": ["turnstile"],
    "recaptcha": ["recaptcha", "g-recaptcha"],
    "hcaptcha": ["hcaptcha"],
    "managed": ["verify you are human", "checking your browser", "bot protection"],
}


class TargetParser(HTMLParser):
    def __init__(self, base_url: str):
        super().__init__(convert_charrefs=True)
        self.base_url = base_url
        self.title = ""
        self.links: list[dict[str, str]] = []
        self.forms: list[dict[str, Any]] = []
        self.page_text: list[str] = []
        self._capture_stack: list[dict[str, Any]] = []
        self._current_form: dict[str, Any] | None = None

    def handle_starttag(self, tag: str, attrs: list[tuple[str, str | None]]) -> None:
        attr_map = {key.lower(): value or "" for key, value in attrs}
        if tag in {"title", "a", "button"}:
            self._capture_stack.append({"tag": tag, "text": [], "href": attr_map.get("href", ""), "attrs": attr_map})

        if tag == "form":
            self._current_form = {
                "action": urljoin(self.base_url, attr_map.get("action", "")) if attr_map.get("action") else "",
                "method": (attr_map.get("method", "get") or "get").lower(),
                "fields": [],
                "buttons": [],
            }

        if tag in {"input", "textarea", "select"} and self._current_form is not None:
            descriptor = {
                "tag": tag,
                "type": attr_map.get("type", tag) or tag,
                "name": attr_map.get("name", ""),
                "id": attr_map.get("id", ""),
                "placeholder": attr_map.get("placeholder", ""),
                "label": attr_map.get("aria-label", "") or attr_map.get("title", ""),
                "required": "required" in attr_map,
            }
            self._current_form["fields"].append(descriptor)
            if tag == "input" and descriptor["type"] in {"submit", "button"}:
                self._current_form["buttons"].append(descriptor["name"] or descriptor["placeholder"] or descriptor["label"] or descriptor["type"])

        if tag == "button" and self._current_form is not None:
            self._current_form["buttons"].append(attr_map.get("aria-label", "") or attr_map.get("title", ""))

    def handle_data(self, data: str) -> None:
        text = re.sub(r"\s+", " ", unescape(data or "")).strip()
        if text:
            self.page_text.append(text)
        if self._capture_stack:
            self._capture_stack[-1]["text"].append(data)

    def handle_endtag(self, tag: str) -> None:
        if tag == "form" and self._current_form is not None:
            self.forms.append(self._current_form)
            self._current_form = None

        if not self._capture_stack or self._capture_stack[-1]["tag"] != tag:
            return
        item = self._capture_stack.pop()
        text = re.sub(r"\s+", " ", unescape(" ".join(item["text"]))).strip()
        if tag == "title" and text:
            self.title = text
        elif tag == "a":
            href = item["href"].strip()
            if href:
                self.links.append({"href": urljoin(self.base_url, href), "text": text})
        elif tag == "button" and self._current_form is not None and text:
            self._current_form["buttons"].append(text)


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
                ["curl", "-LfsS", "--max-time", str(timeout), *extra_args, url],
                capture_output=True,
                text=True,
                check=False,
            )
            if result.returncode == 0 and result.stdout:
                return url, result.stdout
        raise first_error


def parse_page(url: str, timeout: int) -> dict[str, Any]:
    final_url, html = fetch_html(url, timeout)
    parser = TargetParser(final_url)
    parser.feed(html)
    parser.close()
    return {
        "url": final_url,
        "title": parser.title,
        "links": parser.links,
        "forms": parser.forms,
        "page_text": " ".join(unique_notes(parser.page_text, limit=80)),
        "html": html,
    }


def classify_site_type(text: str) -> str:
    lowered = text.lower()
    for site_type, keywords in SITE_TYPE_RULES.items():
        if any(keyword in lowered for keyword in keywords):
            return site_type
    return "unknown"


def detect_auth_type(text: str, links: list[dict[str, str]], forms: list[dict[str, Any]]) -> tuple[str, list[str], bool]:
    lowered = text.lower()
    oauth: list[str] = []
    for provider in ("google", "github", "twitter", "linkedin"):
        provider_patterns = [
            f"sign in with {provider}",
            f"log in with {provider}",
            f"continue with {provider}",
            f"login with {provider}",
            f"connect with {provider}",
        ]
        has_oauth_phrase = any(pattern in lowered for pattern in provider_patterns)
        has_oauth_link = any(
            provider in f"{link.get('href', '')} {link.get('text', '')}".lower()
            and any(marker in f"{link.get('href', '')} {link.get('text', '')}".lower() for marker in ("oauth", "auth", "login", "signin", "sign in"))
            for link in links
        )
        if has_oauth_phrase or has_oauth_link:
            oauth.append(provider)

    has_email_field = any(
        field.get("type", "").lower() == "email" or "email" in " ".join(
            [field.get("name", ""), field.get("placeholder", ""), field.get("label", ""), field.get("id", "")]
        ).lower()
        for form in forms
        for field in form.get("fields", [])
    )
    if forms and not oauth:
        return "none", oauth, False
    if oauth:
        return "google_oauth" if "google" in oauth else "unknown", oauth, True
    if "magic link" in lowered or "email me a link" in lowered:
        return "magic_link", oauth, True
    if has_email_field and any(word in lowered for word in ("sign up", "register", "create account", "log in", "login")):
        return "email_signup", oauth, True
    if forms:
        return "none", oauth, False
    return "unknown", oauth, False


def detect_antibot(text: str, html: str) -> tuple[str, str]:
    lowered = f"{text} {html}".lower()
    for anti_bot, keywords in HARD_ANTI_BOT.items():
        if any(keyword in lowered for keyword in keywords):
            return anti_bot, "managed"

    if "captcha" in lowered:
        if re.search(r"\bwhat is\s+\d+\s*[\+\-*x]\s*\d+\b", lowered):
            return "none", "simple_math"
        if "<img" in html.lower():
            return "none", "simple_image"
        return "none", "simple_text"

    return "none", "none"


def find_submit_links(links: list[dict[str, str]]) -> list[dict[str, str]]:
    matches = []
    for link in links:
        haystack = f"{link.get('href', '')} {link.get('text', '')}".lower()
        if any(hint in haystack for hint in SUBMIT_HINTS):
            matches.append(link)
    return matches


def guess_field_map(forms: list[dict[str, Any]]) -> dict[str, str]:
    patterns = {
        "submitter_name": ["submitter", "your name", "full name", "contact name"],
        "product_name": ["product", "tool", "title", "app name", "tool_name", "product_name"],
        "promoted_url": ["url", "website", "homepage", "site", "link"],
        "primary_email": ["email", "mail"],
        "short_description": ["description", "summary", "intro", "about"],
        "category": ["category", "tag"],
    }
    guessed: dict[str, str] = {}
    for form in forms:
        for field in form.get("fields", []):
            label = " ".join([field.get("name", ""), field.get("placeholder", ""), field.get("label", ""), field.get("id", "")]).lower()
            for canonical, keywords in patterns.items():
                if canonical == "product_name" and any(skip in label for skip in ("submitter", "your name", "contact name")):
                    continue
                if canonical not in guessed and any(keyword in label for keyword in keywords):
                    guessed[canonical] = field.get("name") or field.get("id") or field.get("placeholder") or field.get("label")
    return guessed


def main() -> int:
    parser = argparse.ArgumentParser(description="Scout a target site and classify submission, auth, and anti-bot signals.")
    parser.add_argument("--url", required=True)
    parser.add_argument("--timeout", type=int, default=20)
    parser.add_argument("--deep", action="store_true")
    parser.add_argument("--out", default="")
    args = parser.parse_args()

    root_page = parse_page(normalize_url(args.url), args.timeout)
    submit_links = find_submit_links(root_page["links"])
    scout_page = root_page
    followed_submit_link = ""
    if args.deep and not root_page["forms"] and submit_links:
        followed_submit_link = submit_links[0]["href"]
        scout_page = parse_page(followed_submit_link, args.timeout)

    site_type = classify_site_type(f"{root_page['title']} {root_page['page_text']} {scout_page['page_text']}")
    auth_type, oauth_providers, requires_login = detect_auth_type(
        f"{root_page['page_text']} {scout_page['page_text']}",
        scout_page["links"],
        scout_page["forms"],
    )
    anti_bot, captcha_tier = detect_antibot(f"{root_page['page_text']} {scout_page['page_text']}", scout_page["html"])
    field_map = guess_field_map(scout_page["forms"])
    candidate_submit_url = followed_submit_link or (submit_links[0]["href"] if submit_links else scout_page["url"])

    result = {
        "scouted_at": now_iso(),
        "target_url": normalize_url(args.url),
        "domain": domain_from_url(args.url).removeprefix("www."),
        "host_domain": domain_from_url(args.url),
        "site_type": site_type,
        "auth_type": auth_type,
        "oauth_providers": oauth_providers,
        "requires_login": requires_login,
        "anti_bot": anti_bot,
        "captcha_tier": captcha_tier,
        "candidate_submit_url": candidate_submit_url,
        "submit_links": submit_links[:10],
        "forms": scout_page["forms"],
        "field_map": field_map,
        "titles": {
            "landing": root_page["title"],
            "submit": scout_page["title"],
        },
        "notes": unique_notes(
            [
                f"deep scout followed {followed_submit_link}" if followed_submit_link else "",
                "login appears required" if requires_login else "",
                f"oauth providers: {', '.join(oauth_providers)}" if oauth_providers else "",
                f"anti-bot: {anti_bot}" if anti_bot != "none" else "",
                f"captcha tier: {captcha_tier}" if captcha_tier != "none" else "",
            ],
            limit=12,
        ),
    }

    if args.out:
        out_path = Path(args.out).expanduser().resolve()
        save_json(out_path, result)
        print(json.dumps({"ok": True, "scout_path": str(out_path), "result": result}, ensure_ascii=False, indent=2))
        return 0

    print(json.dumps({"ok": True, "result": result}, ensure_ascii=False, indent=2))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
