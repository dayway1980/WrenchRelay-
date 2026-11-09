"""Dependency-free regression tests for payment redirect boundaries."""
import ast
import sys
import unittest
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "backend"))
from redirect_validation import approved_redirect


FRONTENDS = ["https://www.wrenchrelayllc.com", "https://app.wrenchrelay.com"]


class CheckoutRedirectTests(unittest.TestCase):
    def test_accepts_exact_allowed_origin_with_path_and_query(self):
        url = "https://www.wrenchrelayllc.com/settings/billing?success=1"
        self.assertEqual(approved_redirect(url, FRONTENDS), url)
        self.assertEqual(
            approved_redirect("https://app.wrenchrelay.com", FRONTENDS, origin_only=True),
            "https://app.wrenchrelay.com",
        )

    def test_rejects_all_lookalike_or_external_hosts(self):
        bad = [
            "https://www.wrenchrelayllc.com.attacker.example/checkout",
            "https://www.wrenchrelayllc.com@attacker.example/checkout",
            "https://attacker.example/www.wrenchrelayllc.com",
            "https://www.wrenchrelayllc.com.evil.invalid/",
            "https://www.wrenchrelayllc.com./",
            "https://www.wrenchrelayllc.com:444/",
            "https://www.wrenchrelayllc.com:bad/",
            "//www.wrenchrelayllc.com/settings/billing",
            "https://www.wrenchrelayllc.com\\@evil.invalid/",
            "https://www.wrenchrelayllc.com\r\nX-Hack: y",
            "https://www.wrenchrelayllc.com/#//evil.invalid",
            "http://www.wrenchrelayllc.com/",
            "javascript:alert(1)",
            "",
        ]
        for url in bad:
            with self.subTest(url=url), self.assertRaises(ValueError):
                approved_redirect(url, FRONTENDS)

    def test_origin_only_rejects_path_and_query(self):
        for url in [
            "https://www.wrenchrelayllc.com/settings/billing",
            "https://www.wrenchrelayllc.com/?next=/x",
        ]:
            with self.subTest(url=url), self.assertRaises(ValueError):
                approved_redirect(url, FRONTENDS, origin_only=True)

    def test_invalid_config_fails_closed(self):
        for origins in [[], ["*"], ["https://www.wrenchrelayllc.com/nested"]]:
            with self.subTest(origins=origins), self.assertRaises(ValueError):
                approved_redirect("https://www.wrenchrelayllc.com/x", origins)

    def test_explicit_local_development_origin_can_use_http(self):
        self.assertEqual(
            approved_redirect("http://localhost:3000/settings/billing", ["http://localhost:3000"]),
            "http://localhost:3000/settings/billing",
        )
        with self.assertRaises(ValueError):
            approved_redirect("http://localhost:3000/", FRONTENDS)

    def test_accepts_default_https_port_and_normalized_hostname(self):
        self.assertEqual(
            approved_redirect("https://WWW.WRENCHRELAYLLC.COM:443/settings/billing", FRONTENDS),
            "https://WWW.WRENCHRELAYLLC.COM:443/settings/billing",
        )

    def test_both_checkout_routes_use_validator(self):
        payments = (ROOT / "backend" / "payments_router.py").read_text()
        billing = (ROOT / "backend" / "billing_router.py").read_text()
        ast.parse(payments)
        ast.parse(billing)
        self.assertIn("approved_redirect(payload.successUrl", payments)
        self.assertIn("approved_redirect(payload.cancelUrl", payments)
        self.assertIn("success_url=success_url", payments)
        self.assertIn("cancel_url=cancel_url", payments)
        self.assertIn("_approved_frontend_redirect(payload.origin_url", billing)
        self.assertIn("_approved_frontend_redirect(return_url", billing)


if __name__ == "__main__":
    unittest.main()
