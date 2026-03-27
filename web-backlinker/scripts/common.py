#!/usr/bin/env python3
from __future__ import annotations

import json
import os
import re
from datetime import datetime, timezone
from pathlib import Path
from typing import Any, Iterable, List
from urllib.parse import urlsplit, urlunsplit


def now_iso() -> str:
    return datetime.now(timezone.utc).isoformat()


def default_base_dir() -> Path:
    override = os.environ.get("BACKLINK_HELPER_BASE_DIR")
    if override:
        return Path(override).expanduser()
    return Path(__file__).resolve().parents[1] / "data" / "backlink-helper"


def slugify(value: str) -> str:
    cleaned = re.sub(r"[^a-zA-Z0-9.-]+", "-", (value or "").strip().lower())
    return cleaned.strip("-") or "item"


def load_json(path: Path, default: Any) -> Any:
    if not path.exists():
        return default
    return json.loads(path.read_text(encoding="utf-8"))


def save_json(path: Path, data: Any) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    temp_path = path.with_name(f".{path.name}.tmp")
    temp_path.write_text(
        json.dumps(data, ensure_ascii=False, indent=2) + "\n",
        encoding="utf-8",
    )
    os.replace(temp_path, path)


def append_jsonl(path: Path, event: dict[str, Any]) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    with path.open("a", encoding="utf-8") as handle:
        handle.write(json.dumps(event, ensure_ascii=False) + "\n")


def normalize_url(raw: str, keep_query: bool = True) -> str:
    value = (raw or "").strip()
    if not value:
        return ""
    if not re.match(r"^[a-zA-Z][a-zA-Z0-9+.-]*://", value):
        value = "https://" + value
    parts = urlsplit(value)
    scheme = parts.scheme.lower() or "https"
    netloc = parts.netloc.lower()
    if ":" in netloc:
        host, port = netloc.rsplit(":", 1)
        if (scheme == "https" and port == "443") or (scheme == "http" and port == "80"):
            netloc = host
    path = re.sub(r"/+", "/", parts.path or "/")
    query = parts.query if keep_query else ""
    return urlunsplit((scheme, netloc, path, query, ""))


def normalize_promoted_url(raw: str) -> str:
    return normalize_url(raw, keep_query=False)


def domain_from_url(raw: str) -> str:
    try:
        return urlsplit(normalize_url(raw)).netloc.lower()
    except Exception:
        return ""


def unique_notes(notes: Iterable[str], limit: int = 12) -> List[str]:
    seen: set[str] = set()
    ordered: List[str] = []
    for note in notes:
        cleaned = str(note).strip()
        if not cleaned or cleaned in seen:
            continue
        ordered.append(cleaned)
        seen.add(cleaned)
    return ordered[-limit:]


def read_targets_file(path: Path) -> List[str]:
    values: List[str] = []
    for line in path.read_text(encoding="utf-8").splitlines():
        cleaned = line.strip()
        if not cleaned or cleaned.startswith("#"):
            continue
        values.append(cleaned)
    return values
