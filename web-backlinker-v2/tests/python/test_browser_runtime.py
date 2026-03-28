import sys
import unittest
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(ROOT / "scripts"))

from browser_runtime import resolve_browser_runtime  # noqa: E402


class BrowserRuntimeTests(unittest.TestCase):
    def test_resolve_http_runtime_fetches_playwright_ws(self):
        def fake_fetch(url: str, timeout: int):
            self.assertEqual(url, "http://127.0.0.1:9222/json/version")
            self.assertEqual(timeout, 7)
            return {
                "Browser": "Chrome/145.0.0.0",
                "Protocol-Version": "1.3",
                "User-Agent": "Mozilla/5.0",
                "webSocketDebuggerUrl": "ws://127.0.0.1:9222/devtools/browser/demo",
            }

        runtime = resolve_browser_runtime(cdp_url="127.0.0.1:9222", timeout=7, fetcher=fake_fetch)
        self.assertTrue(runtime["configured"])
        self.assertTrue(runtime["ok"])
        self.assertEqual(runtime["cdp_url"], "http://127.0.0.1:9222")
        self.assertEqual(runtime["playwright_ws_url"], "ws://127.0.0.1:9222/devtools/browser/demo")
        self.assertEqual(runtime["source"], "arg")

    def test_resolve_ws_runtime_skips_http_probe(self):
        runtime = resolve_browser_runtime(cdp_url="ws://host:9222/devtools/browser/abc")
        self.assertTrue(runtime["configured"])
        self.assertTrue(runtime["ok"])
        self.assertEqual(runtime["cdp_url"], "ws://host:9222/devtools/browser/abc")
        self.assertEqual(runtime["playwright_ws_url"], "ws://host:9222/devtools/browser/abc")

    def test_env_fallback_uses_backlink_browser_cdp_url(self):
        runtime = resolve_browser_runtime(
            env={"BACKLINK_BROWSER_CDP_URL": "http://10.0.0.8:9222"},
            fetcher=lambda url, timeout: {"webSocketDebuggerUrl": "ws://10.0.0.8:9222/devtools/browser/demo"},
        )
        self.assertEqual(runtime["source"], "env:BACKLINK_BROWSER_CDP_URL")
        self.assertEqual(runtime["cdp_url"], "http://10.0.0.8:9222")
        self.assertEqual(runtime["playwright_ws_url"], "ws://10.0.0.8:9222/devtools/browser/demo")


if __name__ == "__main__":
    unittest.main()
