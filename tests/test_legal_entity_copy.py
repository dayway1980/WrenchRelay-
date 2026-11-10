"""Check provider-facing frontend statements against WrenchRelay LLC name."""
from pathlib import Path
import unittest

SOURCE = Path(__file__).resolve().parents[1] / "src" / "App.js"

class LegalEntityCopy(unittest.TestCase):
    def test_terms_and_both_footers_name_wrenchrelay_llc(self):
        src = SOURCE.read_text(encoding="utf-8")
        self.assertNotIn("God’s Plan LLC", src)
        self.assertNotIn("God's Plan LLC", src)
        self.assertIn("WrenchRelay is operated by WrenchRelay LLC.", src)
        self.assertEqual(src.count("© 2026 WrenchRelay LLC"), 2)

if __name__ == "__main__":
    unittest.main()
