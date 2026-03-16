#!/usr/bin/env python3
import argparse
import json
import sys
from datetime import datetime, timezone
from pathlib import Path
from typing import Any, Dict, Iterable, List

SCRIPT_DIR = Path(__file__).resolve().parent
if str(SCRIPT_DIR) not in sys.path:
    sys.path.insert(0, str(SCRIPT_DIR))

from task_store import derive_lease_path, load_json, load_store, save_json, sheet_counts  # noqa: E402

NOTE_LIMIT = 10
SHEET_ORDER = ['submitted', 'verified', 'pending_email', 'needs_human', 'failed', 'skipped', 'pending', 'stalled']


def now_iso() -> str:
    return datetime.now(timezone.utc).isoformat()


def compact_notes(notes: Iterable[str], limit: int = NOTE_LIMIT) -> List[str]:
    cleaned = [str(note).strip() for note in notes if str(note).strip()]
    if len(cleaned) > limit:
        return cleaned[-limit:]
    return cleaned


def extract_recent_event_notes(events_path: Path, limit: int) -> List[str]:
    if not events_path.exists() or limit <= 0:
        return []
    lines = events_path.read_text(encoding='utf-8').splitlines()
    notes: List[str] = []
    for line in lines[-limit:]:
        try:
            payload = json.loads(line)
        except Exception:
            continue
        note = payload.get('note') or payload.get('message') or ''
        if note:
            notes.append(str(note).strip())
    return compact_notes(notes, limit)


def build_summary(run_id: str, tasks: List[Dict[str, Any]]) -> str:
    counts = sheet_counts(tasks)
    total = len(tasks)
    ordered = [f'{key}={counts.get(key, 0)}' for key in SHEET_ORDER]
    return f"[WB-SUMMARY] run={run_id} | total={total} | " + ' | '.join(ordered)


def main() -> int:
    parser = argparse.ArgumentParser(description='Refresh a compact Web Backlinker run manifest from task state.')
    parser.add_argument('--manifest', required=True)
    parser.add_argument('--store', required=True)
    parser.add_argument('--events', default='')
    parser.add_argument('--brief-path', default='')
    parser.add_argument('--lease-path', default='')
    parser.add_argument('--state', default='')
    parser.add_argument('--last-worker', default='')
    parser.add_argument('--last-row-id', default='')
    parser.add_argument('--last-domain', default='')
    parser.add_argument('--last-result', default='')
    parser.add_argument('--last-status', default='')
    parser.add_argument('--last-note', default='')
    parser.add_argument('--last-artifact-ref', default='')
    parser.add_argument('--append-note', default='')
    parser.add_argument('--note-limit', type=int, default=NOTE_LIMIT)
    parser.add_argument('--event-note-limit', type=int, default=5)
    args = parser.parse_args()

    manifest_path = Path(args.manifest).expanduser().resolve()
    store_path = Path(args.store).expanduser().resolve()
    events_path = Path(args.events).expanduser().resolve() if args.events else None
    manifest = load_json(manifest_path)
    store = load_store(store_path)
    tasks = store['tasks']

    local_counts: Dict[str, int] = {}
    for task in tasks:
        local_counts[task['status']] = local_counts.get(task['status'], 0) + 1
    compact_sheet_counts = sheet_counts(tasks)

    existing_notes = manifest.get('recent_notes') or manifest.get('notes') or []
    if not existing_notes and events_path:
        existing_notes = extract_recent_event_notes(events_path, args.event_note_limit)
    notes = compact_notes(existing_notes, args.note_limit)
    if args.append_note:
        notes = compact_notes([*notes, args.append_note], args.note_limit)

    manifest['compact_manifest_version'] = 1
    manifest['updated_at'] = now_iso()
    manifest['state'] = args.state or manifest.get('state', '')
    manifest['counts_local'] = local_counts
    manifest['counts_sheet'] = compact_sheet_counts
    manifest['summary'] = build_summary(manifest.get('run_id', ''), tasks)
    manifest['recent_notes'] = notes
    manifest['notes'] = notes
    manifest['task_store_path'] = str(store_path)
    manifest['lease_path'] = str(Path(args.lease_path).expanduser().resolve()) if args.lease_path else manifest.get('lease_path') or str(derive_lease_path(store_path))
    if args.brief_path:
        manifest['worker_brief_path'] = str(Path(args.brief_path).expanduser().resolve())
    elif manifest.get('worker_brief_path'):
        manifest['worker_brief_path'] = manifest['worker_brief_path']

    if args.last_worker:
        manifest['last_worker'] = args.last_worker
    if args.last_row_id:
        manifest['last_row_id'] = args.last_row_id
        manifest['last_processed_row_id'] = args.last_row_id
    if args.last_domain:
        manifest['last_domain'] = args.last_domain
        manifest['last_processed_domain'] = args.last_domain
    if args.last_result:
        manifest['last_result'] = args.last_result
    if args.last_status:
        manifest['last_status'] = args.last_status
    if args.last_artifact_ref:
        manifest['last_artifact_ref'] = args.last_artifact_ref
    if args.last_note:
        manifest['last_note'] = args.last_note
        manifest['recent_notes'] = compact_notes([*manifest['recent_notes'], args.last_note], args.note_limit)
        manifest['notes'] = manifest['recent_notes']

    save_json(manifest_path, manifest)
    print(json.dumps({'ok': True, 'manifest': str(manifest_path), 'summary': manifest['summary']}, ensure_ascii=False, indent=2))
    return 0


if __name__ == '__main__':
    raise SystemExit(main())
