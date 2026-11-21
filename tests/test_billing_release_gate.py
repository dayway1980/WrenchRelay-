"""Dependency-free source smoke checks; NOT a substitute for full payment E2E tests."""
import ast
from pathlib import Path
import unittest

ROOT = Path(__file__).resolve().parents[1]


class BillingReleaseGateSourceTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.server = (ROOT / "server.py").read_text(encoding="utf-8")
        cls.app = (ROOT / "App.js").read_text(encoding="utf-8")
        cls.ast = ast.parse(cls.server)

    def test_checkout_has_explicit_fail_closed_gate(self):
        checkouts = [n for n in ast.walk(self.ast)
                     if isinstance(n, (ast.FunctionDef, ast.AsyncFunctionDef))
                     and n.name == "billing_checkout"]
        self.assertEqual(len(checkouts), 1)
        guards = [n for n in ast.walk(checkouts[0])
                  if isinstance(n, ast.If)
                  and isinstance(n.test, ast.UnaryOp)
                  and isinstance(n.test.op, ast.Not)
                  and isinstance(n.test.operand, ast.Call)
                  and isinstance(n.test.operand.func, ast.Name)
                  and n.test.operand.func.id == "billing_ready"]
        self.assertTrue(guards, "Checkout must fail closed when not commissioned")

    def test_live_billing_defaults_off(self):
        self.assertIn('os.getenv("WRENCHRELAY_BILLING_COMMISSIONED", "")', self.server)
        self.assertIn('key.startswith("sk_live_")', self.server)
        self.assertIn('"billing_commissioned": billing_ready()', self.server)

    def test_frontend_does_not_offer_uncommissioned_checkout(self):
        self.assertIn('config.billing_commissioned?', self.app)
        self.assertIn('if(e.status===402)', self.app)
        self.assertIn("Your unfinished notes remain available.", self.app)

    def test_legal_entity_is_correct(self):
        self.assertIn("WrenchRelay LLC", self.app)
        self.assertNotIn("God’s Plan LLC", self.app)


if __name__ == "__main__":
    unittest.main()
