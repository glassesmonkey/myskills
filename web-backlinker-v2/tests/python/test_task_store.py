import sys
import unittest
from datetime import datetime, timedelta, timezone
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(ROOT / "scripts"))

from task_store import (  # noqa: E402
    choose_claimable_task,
    find_ledger_match,
    release_stale_locks,
    upsert_ledger_record,
)


class TaskStoreTests(unittest.TestCase):
    def test_upsert_ledger_record_dedupes_by_domain(self):
        ledger = {"updated_at": "", "records": []}
        first = upsert_ledger_record(
            ledger=ledger,
            promoted_url="https://example.com/?utm=1",
            target_domain="target.com",
            target_url="https://target.com/submit",
            state="submitted",
            run_id="run-1",
            task_id="task-1",
            listing_url="",
            note="first",
        )
        second = upsert_ledger_record(
            ledger=ledger,
            promoted_url="https://example.com/",
            target_domain="target.com",
            target_url="https://target.com/submit?x=1",
            state="verified",
            run_id="run-2",
            task_id="task-2",
            listing_url="https://target.com/listing/example",
            note="second",
        )
        self.assertEqual(first["target_domain"], "target.com")
        self.assertEqual(len(ledger["records"]), 1)
        self.assertIs(first, second)
        self.assertEqual(second["state"], "verified")
        match = find_ledger_match(ledger, "https://example.com/", "target.com", "https://target.com/submit")
        self.assertIsNotNone(match)

    def test_choose_claimable_task_prefers_ready(self):
        data = {
            "tasks": [
                {"task_id": "waiting", "status": "WAITING_EMAIL", "attempts": 0, "row_id": "row-2"},
                {"task_id": "retry", "status": "RETRYABLE", "attempts": 0, "row_id": "row-3"},
                {"task_id": "ready", "status": "READY", "attempts": 1, "row_id": "row-1"},
            ]
        }
        chosen = choose_claimable_task(data, include_waiting_email=True)
        self.assertEqual(chosen["task_id"], "ready")

    def test_release_stale_locks_requeues_running_tasks(self):
        expired = (datetime.now(timezone.utc) - timedelta(minutes=5)).isoformat()
        data = {
            "tasks": [
                {
                    "task_id": "task-1",
                    "status": "RUNNING",
                    "locked_by": "worker-1",
                    "lock_expires_at": expired,
                }
            ]
        }
        changed = release_stale_locks(data)
        self.assertEqual(changed, 1)
        self.assertEqual(data["tasks"][0]["status"], "RETRYABLE")
        self.assertEqual(data["tasks"][0]["locked_by"], "")


if __name__ == "__main__":
    unittest.main()
