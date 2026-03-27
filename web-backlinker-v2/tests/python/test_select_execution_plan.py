import sys
import unittest
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(ROOT / "scripts"))

from select_execution_plan import choose_plan  # noqa: E402


class SelectExecutionPlanTests(unittest.TestCase):
    def test_hard_antibot_parks_task(self):
        task = {
            "anti_bot": "cloudflare",
            "captcha_tier": "managed",
            "auth_type": "none",
            "site_type": "directory",
        }
        plan = choose_plan(task, {}, None, 0.85, 0.60)
        self.assertEqual(plan["route"], "park_hard_antibot")
        self.assertEqual(plan["execution_mode"], "manual")

    def test_validated_playbook_runs_directly(self):
        task = {
            "anti_bot": "none",
            "captcha_tier": "none",
            "auth_type": "none",
            "site_type": "directory",
        }
        playbook = {
            "playbook_id": "site-demo",
            "steps": [{"action": "open"}],
            "execution_mode": "session_browser",
            "replay_confidence": 0.9,
        }
        plan = choose_plan(task, playbook, None, 0.85, 0.60)
        self.assertEqual(plan["route"], "replay_site_playbook")
        self.assertEqual(plan["automation_disposition"], "AUTO_EXECUTE")


if __name__ == "__main__":
    unittest.main()
