import sys
import unittest
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(ROOT / "scripts"))

from preflight import derive_preflight_summary, resolve_bb_mode  # noqa: E402


class PreflightTests(unittest.TestCase):
    def test_resolve_bb_mode_defaults_to_standalone_for_codex(self):
        self.assertEqual(resolve_bb_mode("auto", True), "standalone_extension")
        self.assertEqual(resolve_bb_mode("auto", False), "standalone_extension")
        self.assertEqual(resolve_bb_mode("mcp", True), "mcp")

    def test_preflight_prefers_browser_use_when_shared_cdp_ready(self):
        summary = derive_preflight_summary(
            {
                "node": {"installed": True, "ok": True},
                "pnpm": {"installed": True, "ok": True},
                "browser_runtime": {"configured": True, "ok": True, "cdp_url": "http://127.0.0.1:9222"},
                "browser_use": {"installed": True, "smoke_ok": True},
                "bb_browser": {"installed": True, "smoke_ok": True, "resolved_mode": "standalone_extension"},
                "gog": {"installed": True, "configured": True},
            }
        )
        self.assertEqual(summary["default_provider"], "browser-use-cli")
        self.assertEqual(summary["bb_browser_mode"], "standalone_extension")
        self.assertTrue(summary["ready_for_real_submit"])
        self.assertEqual(summary["warnings"], [])

    def test_preflight_falls_back_to_bb_browser_when_cdp_unconfigured(self):
        summary = derive_preflight_summary(
            {
                "node": {"installed": True, "ok": True},
                "pnpm": {"installed": True, "ok": True},
                "browser_runtime": {"configured": False, "ok": False},
                "browser_use": {"installed": True, "smoke_ok": False},
                "bb_browser": {"installed": True, "smoke_ok": True, "resolved_mode": "standalone_extension"},
                "gog": {"installed": True, "configured": False},
            }
        )
        self.assertEqual(summary["default_provider"], "bb-browser")
        self.assertTrue(summary["ready_for_real_submit"])
        self.assertIn("gog_unconfigured", summary["warnings"])
        self.assertNotIn("browser_cdp_unconfigured", summary["warnings"])

    def test_preflight_falls_back_to_dry_run_when_no_browser_stack_ready(self):
        summary = derive_preflight_summary(
            {
                "node": {"installed": True, "ok": True},
                "pnpm": {"installed": True, "ok": True},
                "browser_runtime": {"configured": False, "ok": False},
                "browser_use": {"installed": False, "smoke_ok": False},
                "bb_browser": {"installed": False, "smoke_ok": False, "resolved_mode": "disabled"},
                "gog": {"installed": True, "configured": False},
            }
        )
        self.assertEqual(summary["default_provider"], "dry-run")
        self.assertFalse(summary["ready_for_real_submit"])
        self.assertIn("browser_cdp_unconfigured", summary["warnings"])
        self.assertIn("bb_browser_missing", summary["warnings"])
        self.assertIn("gog_unconfigured", summary["warnings"])

    def test_preflight_marks_mcp_as_external_wiring(self):
        summary = derive_preflight_summary(
            {
                "node": {"installed": True, "ok": True},
                "pnpm": {"installed": True, "ok": True},
                "browser_runtime": {"configured": False, "ok": False},
                "browser_use": {"installed": False, "smoke_ok": False},
                "bb_browser": {"installed": True, "smoke_ok": False, "resolved_mode": "mcp"},
                "gog": {"installed": True, "configured": True},
            }
        )
        self.assertEqual(summary["bb_browser_mode"], "mcp")
        self.assertEqual(summary["default_provider"], "dry-run")
        self.assertIn("bb_browser_mcp_requires_external_wiring", summary["warnings"])

    def test_preflight_blocks_openclaw_mode_in_codex(self):
        summary = derive_preflight_summary(
            {
                "node": {"installed": True, "ok": True},
                "pnpm": {"installed": True, "ok": True},
                "browser_runtime": {"configured": False, "ok": False},
                "browser_use": {"installed": False, "smoke_ok": False},
                "bb_browser": {
                    "installed": True,
                    "smoke_ok": False,
                    "resolved_mode": "openclaw",
                    "host_runtime": "codex",
                    "mode_allowed": False,
                },
                "gog": {"installed": True, "configured": True},
            }
        )
        self.assertEqual(summary["host_runtime"], "codex")
        self.assertEqual(summary["default_provider"], "dry-run")
        self.assertFalse(summary["ready_for_real_submit"])
        self.assertIn("bb_browser_mode_not_supported", summary["blockers"])


if __name__ == "__main__":
    unittest.main()
