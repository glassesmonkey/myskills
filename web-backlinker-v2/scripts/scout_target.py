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
CLOUDFLARE_ACTIVE_PATTERNS = [
    "just a moment",
    "checking your browser",
    "/cdn-cgi/challenge-platform/",
    "cf-chl-",
    "cf-browser-verification",
]
MANAGED_CHALLENGE_PATTERNS = [
    "verify you are human",
    "verify that you are human",
    "verify you're human",
    "bot protection",
    "security check",
    "press and hold",
]
TURNSTILE_WIDGET_PATTERNS = [
    "cf-turnstile",
    "challenges.cloudflare.com/turnstile",
    "data-sitekey",
]
RECAPTCHA_WIDGET_PATTERNS = [
    "g-recaptcha",
    'name="g-recaptcha-response"',
    "google.com/recaptcha/api2",
    "www.google.com/recaptcha/api2",
    "grecaptcha.render",
]
HCAPTCHA_WIDGET_PATTERNS = [
    "h-captcha",
    "js.hcaptcha.com",
    "hcaptcha.com/1/api.js",
]
CLOUDFLARE_VENDOR_PATTERNS = [
    "static.cloudflareinsights.com",
    "data-cf-beacon",
]
RECAPTCHA_VENDOR_PATTERNS = [
    "google.com/recaptcha/api.js",
    "www.google.com/recaptcha/api.js",
    "grecaptcha",
]
HCAPTCHA_VENDOR_PATTERNS = [
    "hcaptcha.com/1/api.js",
    "js.hcaptcha.com",
]
CAPTCHA_SIMPLE_IMAGE_PATTERNS = [
    "captcha",
    "security code",
    "verification code",
    "type the characters",
]
CAPTCHA_SIMPLE_TEXT_PATTERNS = [
    "captcha",
    "security code",
    "verification code",
]
RECIPROCAL_BACKLINK_PATTERNS = [
    "reciprocal backlink",
    "reciprocal link",
    "backlink required",
    "require a backlink",
    "requires a backlink",
    "require backlink",
    "requires backlink",
    "must link to us",
    "link back to us",
    "backlink to us",
    "exchange links",
    "link exchange",
    "swap links",
    "add our link",
    "place our link",
    "add our badge",
    "place our badge",
]
RECIPROCAL_BADGE_PATTERNS = [
    "our badge",
    "put this badge on your website",
    "place this badge on your website",
    "add the following code to your website",
    "copy and paste this code into your website",
]


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
    for provider in ("google", "facebook", "github", "twitter", "linkedin"):
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

    field_descriptors = [
        (
            field,
            " ".join([field.get("name", ""), field.get("placeholder", ""), field.get("label", ""), field.get("id", "")]).lower(),
        )
        for form in forms
        for field in form.get("fields", [])
    ]
    has_email_field = any(field.get("type", "").lower() == "email" or "email" in field_text for field, field_text in field_descriptors)
    has_password_field = any(field.get("type", "").lower() == "password" or "password" in field_text for field, field_text in field_descriptors)
    auth_words = ("sign up", "register", "create account", "log in", "login", "sign in", "password", "forgot your password")

    if oauth:
        if "google" in oauth:
            return "google_oauth", oauth, True
        if "facebook" in oauth:
            return "facebook_oauth", oauth, True
        return "oauth", oauth, True
    if "magic link" in lowered or "email me a link" in lowered:
        return "magic_link", oauth, True
    if has_password_field and any(word in lowered for word in auth_words):
        return "email_signup", oauth, True
    if has_email_field and any(word in lowered for word in auth_words):
        return "email_signup", oauth, True
    if forms:
        return "none", oauth, False
    return "unknown", oauth, False


def _has_any(lowered: str, patterns: list[str]) -> bool:
    return any(pattern in lowered for pattern in patterns)


def detect_security_signals(text: str, html: str) -> dict[str, Any]:
    lowered_text = str(text or "").lower()
    lowered_html = str(html or "").lower()
    combined = f"{lowered_text} {lowered_html}"
    visible_or_form_captcha = bool(
        re.search(r"(?<!re)(?<!h)captcha", lowered_text)
        or re.search(r"(?<!re)(?<!h)captcha", lowered_html.replace("g-recaptcha", " ").replace("hcaptcha", " "))
           and any(marker in lowered_html for marker in ("name=\"captcha", "id=\"captcha", "placeholder=\"captcha", "security code", "verification code"))
    )

    vendors: list[str] = []
    if _has_any(lowered_html, CLOUDFLARE_VENDOR_PATTERNS):
        vendors.append("cloudflare-insights")
    if _has_any(lowered_html, RECAPTCHA_VENDOR_PATTERNS):
        vendors.append("recaptcha-script")
    if _has_any(lowered_html, HCAPTCHA_VENDOR_PATTERNS):
        vendors.append("hcaptcha-script")

    evidence: list[str] = []

    if _has_any(combined, CLOUDFLARE_ACTIVE_PATTERNS):
        return {
            "anti_bot": "cloudflare",
            "captcha_tier": "managed",
            "security_vendors": vendors,
            "challenge_active": True,
            "challenge_evidence": ["cloudflare-active-challenge"],
        }

    if _has_any(combined, MANAGED_CHALLENGE_PATTERNS):
        return {
            "anti_bot": "managed",
            "captcha_tier": "managed",
            "security_vendors": vendors,
            "challenge_active": True,
            "challenge_evidence": ["managed-human-verification-copy"],
        }

    if _has_any(lowered_html, TURNSTILE_WIDGET_PATTERNS) and ("turnstile" in lowered_html or "cf-turnstile" in lowered_html):
        evidence.append("turnstile-widget")
        return {
            "anti_bot": "turnstile",
            "captcha_tier": "managed",
            "security_vendors": unique_notes(vendors + ["turnstile-widget"]),
            "challenge_active": True,
            "challenge_evidence": evidence,
        }

    if _has_any(lowered_html, RECAPTCHA_WIDGET_PATTERNS):
        evidence.append("recaptcha-widget")
        return {
            "anti_bot": "recaptcha",
            "captcha_tier": "managed",
            "security_vendors": unique_notes(vendors),
            "challenge_active": True,
            "challenge_evidence": evidence,
        }

    if _has_any(lowered_html, HCAPTCHA_WIDGET_PATTERNS):
        evidence.append("hcaptcha-widget")
        return {
            "anti_bot": "hcaptcha",
            "captcha_tier": "managed",
            "security_vendors": unique_notes(vendors),
            "challenge_active": True,
            "challenge_evidence": evidence,
        }

    if re.search(r"\bwhat is\s+\d+\s*[\+\-*x]\s*\d+\b", combined):
        return {
            "anti_bot": "none",
            "captcha_tier": "simple_math",
            "security_vendors": unique_notes(vendors),
            "challenge_active": False,
            "challenge_evidence": ["simple-math-captcha"],
        }

    if visible_or_form_captcha and _has_any(combined, CAPTCHA_SIMPLE_IMAGE_PATTERNS):
        image_like = any(
            pattern in lowered_html
            for pattern in (
                "captcha-image",
                "captcha_img",
                "captchaimg",
                "captcha.jpg",
                "captcha.png",
                "captcha.gif",
                "security-code",
                "verification-code",
                "<canvas",
            )
        )
        if image_like:
            return {
                "anti_bot": "none",
                "captcha_tier": "simple_image",
                "security_vendors": unique_notes(vendors),
                "challenge_active": False,
                "challenge_evidence": ["simple-image-captcha"],
            }

    if visible_or_form_captcha and _has_any(lowered_text, CAPTCHA_SIMPLE_TEXT_PATTERNS):
        return {
            "anti_bot": "none",
            "captcha_tier": "simple_text",
            "security_vendors": unique_notes(vendors),
            "challenge_active": False,
            "challenge_evidence": ["simple-text-captcha"],
        }

    return {
        "anti_bot": "none",
        "captcha_tier": "none",
        "security_vendors": unique_notes(vendors),
        "challenge_active": False,
        "challenge_evidence": [],
    }


def detect_reciprocal_backlink_requirement(text: str, html: str) -> dict[str, Any]:
    combined = f"{text} {html}".lower()
    evidence = [pattern for pattern in RECIPROCAL_BACKLINK_PATTERNS if pattern in combined]
    badge_required = any(pattern in combined for pattern in RECIPROCAL_BADGE_PATTERNS)
    if badge_required and any(token in combined for token in ("backlink", "link back", "reciprocal", "exchange links", "link exchange")):
        evidence.append("badge/html snippet")
    return {
        "required": bool(evidence),
        "evidence": unique_notes(evidence, limit=6),
    }


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
    security = detect_security_signals(f"{root_page['page_text']} {scout_page['page_text']}", scout_page["html"])
    reciprocal = detect_reciprocal_backlink_requirement(f"{root_page['page_text']} {scout_page['page_text']}", scout_page["html"])
    anti_bot = security["anti_bot"]
    captcha_tier = security["captcha_tier"]
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
        "requires_reciprocal_backlink": reciprocal["required"],
        "blocker_type": "reciprocal_backlink_required" if reciprocal["required"] else "",
        "reciprocal_evidence": reciprocal["evidence"],
        "security_vendors": security["security_vendors"],
        "challenge_active": security["challenge_active"],
        "challenge_evidence": security["challenge_evidence"],
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
                "reciprocal backlink required" if reciprocal["required"] else "",
                f"reciprocal evidence: {', '.join(reciprocal['evidence'])}" if reciprocal["evidence"] else "",
                f"security vendors: {', '.join(security['security_vendors'])}" if security["security_vendors"] else "",
                f"challenge evidence: {', '.join(security['challenge_evidence'])}" if security["challenge_evidence"] else "",
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
