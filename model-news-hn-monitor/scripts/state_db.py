#!/usr/bin/env python3
import argparse
import datetime as dt
import hashlib
import json
import re
import sqlite3
from pathlib import Path
from zoneinfo import ZoneInfo

TIER_MAP = {"rumor": 1, "semi": 2, "official": 3}
REV_TIER_MAP = {v: k for k, v in TIER_MAP.items()}
CONCRETE_EVIDENCE = {
    "official_blog",
    "official_docs",
    "hf",
    "github",
    "openrouter",
    "api_model_id",
    "weight_release",
    "model_card",
}


def now_dt() -> dt.datetime:
    return dt.datetime.now(dt.timezone.utc).replace(microsecond=0)


def now_iso() -> str:
    return now_dt().isoformat()


def normalize_text(value: str) -> str:
    value = (value or "").strip().lower()
    value = re.sub(r"https?://", "", value)
    value = re.sub(r"[^a-z0-9]+", "-", value)
    value = re.sub(r"-+", "-", value).strip("-")
    return value


def normalize_url(url: str) -> str:
    url = (url or "").strip()
    if not url:
        return ""
    url = re.sub(r"#.*$", "", url)
    url = re.sub(r"/$", "", url)
    return url


def derive_item_key(vendor: str, model_name: str, title: str) -> str:
    base = "::".join(
        part for part in [normalize_text(vendor), normalize_text(model_name), normalize_text(title)] if part
    )
    if not base:
        raise SystemExit("Cannot derive item key without vendor/model/title")
    digest = hashlib.sha1(base.encode("utf-8")).hexdigest()[:16]
    slug = "-".join(part for part in [normalize_text(vendor), normalize_text(model_name)] if part) or normalize_text(title)[:48]
    slug = slug[:64].strip("-") or "item"
    return f"{slug}-{digest}"


def connect(db_path: str) -> sqlite3.Connection:
    path = Path(db_path)
    path.parent.mkdir(parents=True, exist_ok=True)
    conn = sqlite3.connect(str(path))
    conn.row_factory = sqlite3.Row
    conn.execute("PRAGMA foreign_keys = ON")
    return conn


def init_db(conn: sqlite3.Connection) -> None:
    conn.executescript(
        """
        CREATE TABLE IF NOT EXISTS items (
          item_key TEXT PRIMARY KEY,
          vendor TEXT,
          model_name TEXT,
          title TEXT NOT NULL,
          canonical_url TEXT,
          first_seen TEXT NOT NULL,
          last_seen TEXT NOT NULL,
          highest_tier INTEGER NOT NULL DEFAULT 0,
          status TEXT NOT NULL DEFAULT 'queued',
          notes TEXT
        );

        CREATE TABLE IF NOT EXISTS signals (
          id INTEGER PRIMARY KEY AUTOINCREMENT,
          item_key TEXT NOT NULL REFERENCES items(item_key) ON DELETE CASCADE,
          source_kind TEXT NOT NULL,
          source_label TEXT NOT NULL,
          source_url TEXT NOT NULL,
          observed_at TEXT NOT NULL,
          tier INTEGER NOT NULL,
          evidence_json TEXT NOT NULL DEFAULT '[]',
          raw_title TEXT,
          canonical_url TEXT,
          UNIQUE(item_key, source_url)
        );

        CREATE TABLE IF NOT EXISTS posts (
          id INTEGER PRIMARY KEY AUTOINCREMENT,
          item_key TEXT NOT NULL UNIQUE REFERENCES items(item_key) ON DELETE CASCADE,
          submitted_url TEXT NOT NULL,
          hn_url TEXT,
          submitted_at TEXT NOT NULL,
          title_used TEXT NOT NULL,
          notes TEXT
        );

        CREATE TABLE IF NOT EXISTS meta (
          key TEXT PRIMARY KEY,
          value TEXT NOT NULL
        );
        """
    )
    conn.commit()


def meta_get(conn: sqlite3.Connection, key: str, default=None):
    row = conn.execute("SELECT value FROM meta WHERE key = ?", (key,)).fetchone()
    return row["value"] if row else default


def meta_set(conn: sqlite3.Connection, key: str, value) -> None:
    conn.execute(
        "INSERT INTO meta(key, value) VALUES(?, ?) ON CONFLICT(key) DO UPDATE SET value = excluded.value",
        (key, str(value)),
    )


def item_count(conn: sqlite3.Connection) -> int:
    row = conn.execute("SELECT COUNT(*) AS c FROM items").fetchone()
    return int(row["c"])


def fetch_item_snapshot(conn: sqlite3.Connection, item_key: str):
    item = conn.execute("SELECT * FROM items WHERE item_key = ?", (item_key,)).fetchone()
    if not item:
        raise SystemExit(f"Unknown item_key: {item_key}")

    signals = conn.execute(
        "SELECT source_label, source_url, tier, evidence_json FROM signals WHERE item_key = ? ORDER BY observed_at ASC",
        (item_key,),
    ).fetchall()
    post = conn.execute("SELECT * FROM posts WHERE item_key = ?", (item_key,)).fetchone()

    distinct_sources = len({row["source_label"] for row in signals})
    all_evidence = []
    for row in signals:
        try:
            all_evidence.extend(json.loads(row["evidence_json"] or "[]"))
        except json.JSONDecodeError:
            pass
    evidence_set = sorted(set(all_evidence))
    has_concrete = any(e in CONCRETE_EVIDENCE for e in evidence_set)
    ready_to_post = bool(
        not post
        and item["canonical_url"]
        and (
            item["highest_tier"] >= TIER_MAP["official"]
            or (distinct_sources >= 2 and has_concrete)
        )
        and item["status"] in {"queued", "review", "ready"}
    )

    return {
        "item_key": item["item_key"],
        "vendor": item["vendor"],
        "model_name": item["model_name"],
        "title": item["title"],
        "canonical_url": item["canonical_url"],
        "first_seen": item["first_seen"],
        "last_seen": item["last_seen"],
        "highest_tier": REV_TIER_MAP.get(item["highest_tier"], item["highest_tier"]),
        "status": item["status"],
        "signal_count": len(signals),
        "distinct_sources": distinct_sources,
        "evidence": evidence_set,
        "has_concrete_evidence": has_concrete,
        "posted": bool(post),
        "post": dict(post) if post else None,
        "ready_to_post": ready_to_post,
    }


def cmd_init(args):
    conn = connect(args.db)
    init_db(conn)
    print(json.dumps({"ok": True, "db": args.db}, ensure_ascii=False))


def cmd_ingest(args):
    conn = connect(args.db)
    init_db(conn)
    observed_at = args.observed_at or now_iso()
    tier = TIER_MAP[args.tier]
    item_key = args.item_key or derive_item_key(args.vendor or "", args.model_name or "", args.title or "")
    canonical_url = normalize_url(args.canonical_url or "")
    source_url = normalize_url(args.source_url)
    evidence_json = json.dumps(sorted(set(args.evidence or [])), ensure_ascii=False)

    existing = conn.execute("SELECT * FROM items WHERE item_key = ?", (item_key,)).fetchone()
    if existing:
        new_title = args.title if len(args.title or "") > len(existing["title"] or "") else existing["title"]
        new_canonical = canonical_url or existing["canonical_url"]
        conn.execute(
            """
            UPDATE items
            SET vendor = COALESCE(?, vendor),
                model_name = COALESCE(?, model_name),
                title = ?,
                canonical_url = ?,
                last_seen = ?,
                highest_tier = CASE WHEN highest_tier > ? THEN highest_tier ELSE ? END,
                status = CASE WHEN status = 'posted' THEN status ELSE COALESCE(?, status) END
            WHERE item_key = ?
            """,
            (
                args.vendor,
                args.model_name,
                new_title,
                new_canonical,
                observed_at,
                tier,
                tier,
                args.status,
                item_key,
            ),
        )
    else:
        conn.execute(
            """
            INSERT INTO items(item_key, vendor, model_name, title, canonical_url, first_seen, last_seen, highest_tier, status, notes)
            VALUES(?,?,?,?,?,?,?,?,?,?)
            """,
            (
                item_key,
                args.vendor,
                args.model_name,
                args.title,
                canonical_url,
                observed_at,
                observed_at,
                tier,
                args.status or "queued",
                args.notes,
            ),
        )

    conn.execute(
        """
        INSERT OR IGNORE INTO signals(item_key, source_kind, source_label, source_url, observed_at, tier, evidence_json, raw_title, canonical_url)
        VALUES(?,?,?,?,?,?,?,?,?)
        """,
        (
            item_key,
            args.source_kind,
            args.source_label,
            source_url,
            observed_at,
            tier,
            evidence_json,
            args.title,
            canonical_url,
        ),
    )
    conn.commit()
    print(json.dumps(fetch_item_snapshot(conn, item_key), ensure_ascii=False, indent=2))


def cmd_ready(args):
    conn = connect(args.db)
    init_db(conn)
    rows = conn.execute("SELECT item_key FROM items ORDER BY last_seen DESC").fetchall()
    ready = []
    lookback_cutoff = None
    same_local_date = None
    same_local_tz = None
    if args.lookback_hours:
        lookback_cutoff = (now_dt() - dt.timedelta(hours=args.lookback_hours)).isoformat()
    if args.same_day_tz:
        same_local_tz = ZoneInfo(args.same_day_tz)
        same_local_date = now_dt().astimezone(same_local_tz).date()

    for row in rows:
        snap = fetch_item_snapshot(conn, row["item_key"])
        if not snap["ready_to_post"]:
            continue
        if args.min_tier and TIER_MAP[snap["highest_tier"]] < TIER_MAP[args.min_tier]:
            continue
        if lookback_cutoff and snap["last_seen"] < lookback_cutoff:
            continue
        if same_local_date is not None:
            first_seen_local = dt.datetime.fromisoformat(snap["first_seen"]).astimezone(same_local_tz).date()
            if first_seen_local != same_local_date:
                continue
        ready.append(snap)
        if args.limit and len(ready) >= args.limit:
            break
    print(json.dumps(ready, ensure_ascii=False, indent=2))


def cmd_mark_posted(args):
    conn = connect(args.db)
    init_db(conn)
    submitted_at = args.submitted_at or now_iso()
    conn.execute(
        """
        INSERT INTO posts(item_key, submitted_url, hn_url, submitted_at, title_used, notes)
        VALUES(?,?,?,?,?,?)
        ON CONFLICT(item_key) DO UPDATE SET
          submitted_url=excluded.submitted_url,
          hn_url=excluded.hn_url,
          submitted_at=excluded.submitted_at,
          title_used=excluded.title_used,
          notes=excluded.notes
        """,
        (args.item_key, normalize_url(args.submitted_url), normalize_url(args.hn_url or ""), submitted_at, args.title_used, args.notes),
    )
    conn.execute("UPDATE items SET status = 'posted', last_seen = ? WHERE item_key = ?", (submitted_at, args.item_key))
    conn.commit()
    print(json.dumps(fetch_item_snapshot(conn, args.item_key), ensure_ascii=False, indent=2))


def cmd_set_status(args):
    conn = connect(args.db)
    init_db(conn)
    conn.execute("UPDATE items SET status = ?, last_seen = ? WHERE item_key = ?", (args.status, now_iso(), args.item_key))
    conn.commit()
    print(json.dumps(fetch_item_snapshot(conn, args.item_key), ensure_ascii=False, indent=2))


def cmd_posts(args):
    conn = connect(args.db)
    init_db(conn)
    params = []
    sql = "SELECT * FROM posts"
    if args.hours:
        cutoff = (now_dt() - dt.timedelta(hours=args.hours)).isoformat()
        sql += " WHERE submitted_at >= ?"
        params.append(cutoff)
    sql += " ORDER BY submitted_at DESC"
    rows = [dict(r) for r in conn.execute(sql, params).fetchall()]
    print(json.dumps(rows, ensure_ascii=False, indent=2))


def cmd_show(args):
    conn = connect(args.db)
    init_db(conn)
    print(json.dumps(fetch_item_snapshot(conn, args.item_key), ensure_ascii=False, indent=2))


def cmd_tick_monitor(args):
    conn = connect(args.db)
    init_db(conn)
    run_count = int(meta_get(conn, "monitor_run_count", "0")) + 1
    meta_set(conn, "monitor_run_count", run_count)
    meta_set(conn, "last_monitor_tick", now_iso())
    bootstrap_mode = run_count <= args.seed_only_runs
    conn.commit()
    print(
        json.dumps(
            {
                "run_count": run_count,
                "seed_only_runs": args.seed_only_runs,
                "bootstrap_mode": bootstrap_mode,
                "item_count": item_count(conn),
                "message": "seed-only bootstrap run: ingest and classify, but do not auto-post" if bootstrap_mode else "posting enabled",
            },
            ensure_ascii=False,
            indent=2,
        )
    )


def build_parser():
    p = argparse.ArgumentParser(description="Persistent state store for model-news-hn-monitor")
    sub = p.add_subparsers(dest="cmd", required=True)

    init_p = sub.add_parser("init")
    init_p.add_argument("--db", required=True)
    init_p.set_defaults(func=cmd_init)

    ingest_p = sub.add_parser("ingest")
    ingest_p.add_argument("--db", required=True)
    ingest_p.add_argument("--title", required=True)
    ingest_p.add_argument("--source-kind", required=True)
    ingest_p.add_argument("--source-label", required=True)
    ingest_p.add_argument("--source-url", required=True)
    ingest_p.add_argument("--tier", choices=sorted(TIER_MAP.keys()), default="rumor")
    ingest_p.add_argument("--vendor")
    ingest_p.add_argument("--model-name")
    ingest_p.add_argument("--canonical-url")
    ingest_p.add_argument("--evidence", action="append", default=[])
    ingest_p.add_argument("--item-key")
    ingest_p.add_argument("--status")
    ingest_p.add_argument("--notes")
    ingest_p.add_argument("--observed-at")
    ingest_p.set_defaults(func=cmd_ingest)

    ready_p = sub.add_parser("ready")
    ready_p.add_argument("--db", required=True)
    ready_p.add_argument("--min-tier", choices=sorted(TIER_MAP.keys()))
    ready_p.add_argument("--limit", type=int, default=20)
    ready_p.add_argument("--lookback-hours", type=int)
    ready_p.add_argument("--same-day-tz", help="Only return items whose first_seen falls on today's local date in the given IANA timezone")
    ready_p.set_defaults(func=cmd_ready)

    posted_p = sub.add_parser("mark-posted")
    posted_p.add_argument("--db", required=True)
    posted_p.add_argument("--item-key", required=True)
    posted_p.add_argument("--submitted-url", required=True)
    posted_p.add_argument("--hn-url")
    posted_p.add_argument("--title-used", required=True)
    posted_p.add_argument("--notes")
    posted_p.add_argument("--submitted-at")
    posted_p.set_defaults(func=cmd_mark_posted)

    status_p = sub.add_parser("set-status")
    status_p.add_argument("--db", required=True)
    status_p.add_argument("--item-key", required=True)
    status_p.add_argument("--status", required=True)
    status_p.set_defaults(func=cmd_set_status)

    posts_p = sub.add_parser("posts")
    posts_p.add_argument("--db", required=True)
    posts_p.add_argument("--hours", type=int)
    posts_p.set_defaults(func=cmd_posts)

    show_p = sub.add_parser("show")
    show_p.add_argument("--db", required=True)
    show_p.add_argument("--item-key", required=True)
    show_p.set_defaults(func=cmd_show)

    tick_p = sub.add_parser("tick-monitor")
    tick_p.add_argument("--db", required=True)
    tick_p.add_argument("--seed-only-runs", type=int, default=2)
    tick_p.set_defaults(func=cmd_tick_monitor)
    return p


if __name__ == "__main__":
    parser = build_parser()
    args = parser.parse_args()
    args.func(args)
