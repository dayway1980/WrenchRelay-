"""Staging must never access live resources by sharing production secrets."""
import os
import sys
import unittest
from pathlib import Path
from unittest.mock import patch

sys.path.insert(0, str(Path(__file__).resolve().parent))
from release_safety import allow_external_services, unisolated_preview
from realtime_voice import realtime_enabled


class PreviewSafetyTests(unittest.TestCase):
    def test_unisolated_preview_blocks_all_services(self):
        env = {"VERCEL_ENV": "preview", "MONGO_URL": "mongodb://production.example", "OPENAI_API_KEY": "sk-test"}
        self.assertTrue(unisolated_preview(env))
        self.assertFalse(allow_external_services(env))

    def test_preview_requires_explicit_isolation_attestation(self):
        env = {"VERCEL_ENV": "preview", "WRENCHRELAY_PREVIEW_ISOLATED_BACKEND": "true"}
        self.assertFalse(unisolated_preview(env))

    def test_real_production_is_not_blocked_by_preview_guard(self):
        self.assertFalse(unisolated_preview({"VERCEL_ENV": "production"}))
        self.assertTrue(allow_external_services({"VERCEL_ENV": "production"}))

    def test_preview_realtime_stays_off_despite_accidental_flags(self):
        flags = {
            "VERCEL_ENV": "preview",
            "WRENCHRELAY_PREVIEW_ISOLATED_BACKEND": "",
            "WRENCHRELAY_REALTIME_ENABLED": "true",
            "WRENCHRELAY_REALTIME_BUDGET_APPROVED": "true",
            "OPENAI_API_KEY": "sk-test-only",
        }
        with patch.dict(os.environ, flags):
            self.assertFalse(realtime_enabled())


if __name__ == "__main__":
    unittest.main()
