import sys
import unittest
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(ROOT / "scripts"))

from scout_target import detect_auth_type, detect_security_signals  # noqa: E402


class ScoutTargetSecurityTests(unittest.TestCase):
    def test_vendor_scripts_do_not_imply_active_challenge(self):
        html = '''
        <html><head>
          <script defer src="https://static.cloudflareinsights.com/beacon.min.js"></script>
          <script src="https://www.google.com/recaptcha/api.js?render=site-key"></script>
        </head><body>
          <form><input name="email"></form>
        </body></html>
        '''
        result = detect_security_signals("submit tool page", html)
        self.assertEqual(result["anti_bot"], "none")
        self.assertEqual(result["captcha_tier"], "none")
        self.assertFalse(result["challenge_active"])
        self.assertIn("cloudflare-insights", result["security_vendors"])
        self.assertIn("recaptcha-script", result["security_vendors"])

    def test_cloudflare_challenge_page_is_managed(self):
        html = '<html><title>Just a moment...</title><body>Checking your browser before accessing the site. /cdn-cgi/challenge-platform/</body></html>'
        result = detect_security_signals("Just a moment... Checking your browser", html)
        self.assertEqual(result["anti_bot"], "cloudflare")
        self.assertEqual(result["captcha_tier"], "managed")
        self.assertTrue(result["challenge_active"])

    def test_recaptcha_widget_counts_as_managed(self):
        html = '''
        <html><body>
          <form>
            <div class="g-recaptcha" data-sitekey="abc"></div>
            <textarea name="g-recaptcha-response"></textarea>
          </form>
        </body></html>
        '''
        result = detect_security_signals("Please verify you are human", html)
        self.assertEqual(result["anti_bot"], "managed")
        self.assertEqual(result["captcha_tier"], "managed")
        self.assertTrue(result["challenge_active"])

    def test_simple_math_captcha_stays_simple(self):
        html = '<html><body><label>Captcha</label><input name="captcha"><div>What is 4 + 3?</div></body></html>'
        result = detect_security_signals("Captcha What is 4 + 3?", html)
        self.assertEqual(result["anti_bot"], "none")
        self.assertEqual(result["captcha_tier"], "simple_math")
        self.assertFalse(result["challenge_active"])


class ScoutTargetAuthTests(unittest.TestCase):
    def test_login_form_counts_as_requires_login(self):
        text = 'Login Sign in to add your favorites and write reviews Forgot your password'
        forms = [
            {
                "fields": [
                    {"type": "email", "name": "email", "placeholder": "E-Mail Address", "label": "", "id": "email"},
                    {"type": "password", "name": "password", "placeholder": "Password", "label": "", "id": "password"},
                ]
            }
        ]
        auth_type, oauth, requires_login = detect_auth_type(text, [], forms)
        self.assertEqual(auth_type, "email_signup")
        self.assertEqual(oauth, [])
        self.assertTrue(requires_login)


if __name__ == "__main__":
    unittest.main()
