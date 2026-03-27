import json
import subprocess
import sys
import tempfile
import unittest
from pathlib import Path


ROOT = Path(__file__).resolve().parents[2]


class InitIntakeTests(unittest.TestCase):
    def test_init_intake_blocks_until_required_fields_present(self):
        with tempfile.TemporaryDirectory() as temp_dir:
            temp_path = Path(temp_dir)
            bootstrap = subprocess.run(
                [
                    sys.executable,
                    str(ROOT / "scripts" / "bootstrap_runtime.py"),
                    "--base-dir",
                    str(temp_path / "data"),
                    "--campaign",
                    "test",
                    "--promoted-url",
                    "https://example.com",
                ],
                capture_output=True,
                text=True,
                check=True,
            )
            manifest = json.loads(bootstrap.stdout)["manifest"]
            manifest_path = Path(manifest["paths"]["manifest_path"])
            profile_path = Path(manifest["paths"]["profile_path"])
            profile_path.write_text(
                json.dumps(
                    {
                        "product_name": "Example Product",
                        "canonical_url": "https://example.com/",
                        "one_liner": "Example one liner",
                        "short_description": "Short description",
                        "medium_description": "Medium description",
                        "facts": {"contact_emails": ["team@example.com"]},
                    }
                )
                + "\n",
                encoding="utf-8",
            )

            first = subprocess.run(
                [sys.executable, str(ROOT / "scripts" / "init_intake.py"), "--manifest", str(manifest_path)],
                capture_output=True,
                text=True,
                check=True,
            )
            first_payload = json.loads(first.stdout)
            self.assertEqual(first_payload["status"], "WAITING_CONFIG")
            self.assertIn("category_primary", first_payload["required_missing"])
            self.assertTrue(first_payload["friendly_questions_zh"])
            self.assertTrue(first_payload["reply_template_zh"])

            second = subprocess.run(
                [
                    sys.executable,
                    str(ROOT / "scripts" / "init_intake.py"),
                    "--manifest",
                    str(manifest_path),
                    "--set",
                    "category_primary=Music Generator",
                    "--set",
                    "target_audience=Creators",
                    "--set",
                    "use_cases=song demos,jingles",
                    "--set",
                    "submitter_name=Alex",
                    "--set",
                    "primary_email=team@example.com",
                    "--set",
                    "company_email=team@example.com",
                    "--set",
                    "preferred_verification_email=team@example.com",
                    "--set",
                    "allow_gmail_signup=允许",
                    "--set",
                    "allow_company_email_signup=允许",
                    "--set",
                    "allow_oauth_login=允许",
                    "--set",
                    "allow_manual_captcha=不允许",
                    "--set",
                    "allow_paid_listing=不允许",
                    "--set",
                    "allow_reciprocal_backlink=不允许",
                    "--set",
                    "allow_founder_identity_disclosure=不允许",
                    "--set",
                    "allow_phone_disclosure=不允许",
                    "--set",
                    "allow_address_disclosure=不允许",
                ],
                capture_output=True,
                text=True,
                check=True,
            )
            second_payload = json.loads(second.stdout)
            self.assertEqual(second_payload["status"], "READY")
            self.assertEqual(second_payload["required_missing"], [])
            self.assertEqual(second_payload["intake"]["allow_gmail_signup"], True)
            self.assertEqual(second_payload["intake"]["allow_paid_listing"], False)


if __name__ == "__main__":
    unittest.main()
