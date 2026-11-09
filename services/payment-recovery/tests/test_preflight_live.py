import os
from pathlib import Path
import sqlite3
import tempfile
import unittest
from preflight_live import preflight, verified_snapshot, inspect_host


class PreflightTests(unittest.TestCase):
    def setUp(self):
        self.temp = tempfile.TemporaryDirectory()
        self.addCleanup(self.temp.cleanup)
        self.root = Path(self.temp.name)
        source = self.root / "host" / "backend" / "app.py"
        source.parent.mkdir(parents=True)
        source.write_text("app = object()\nDB_PATH = object()\ndef current_user(auth): return None\n")
        self.host = self.root / "host"
        self.db = self.root / "db" / "app.sqlite"
        self.db.parent.mkdir()
        with sqlite3.connect(self.db) as conn:
            for table in ("users", "billing_accounts", "stripe_events"):
                conn.execute(f'CREATE TABLE {table}(id TEXT PRIMARY KEY)')
        self.backups = self.root / "backups"
        self.backups.mkdir(mode=0o700)
        os.chmod(self.backups, 0o700)

    def test_preflight_readonly(self):
        value = preflight(self.host, self.db)
        self.assertEqual(value["sqlite_quick_check"], "ok")
        self.assertFalse(value["billing_commissioned"])
        self.assertEqual(value["backup"], "not_requested")

    def test_verified_backup(self):
        result = preflight(self.host, self.db, self.backups)
        self.assertIn("integrity_verified", result["backup"])
        files = list(self.backups.glob("*.sqlite"))
        self.assertEqual(len(files), 1)
        self.assertEqual(files[0].stat().st_mode & 0o777, 0o600)
        with sqlite3.connect(files[0]) as db:
            self.assertEqual(db.execute("PRAGMA integrity_check").fetchone()[0], "ok")

    def test_missing_schema_denied(self):
        with sqlite3.connect(self.db) as conn:
            conn.execute("DROP TABLE stripe_events")
        with self.assertRaisesRegex(RuntimeError, "tables missing"):
            preflight(self.host, self.db)
        self.assertEqual(list(self.backups.iterdir()), [])

    def test_public_backup_dir_denied(self):
        os.chmod(self.backups, 0o755)
        with self.assertRaisesRegex(RuntimeError, "private"):
            verified_snapshot(self.db, self.backups)

    def test_unreviewable_host_rejected(self):
        (self.host / "backend" / "app.py").write_text("app = object()\n")
        with self.assertRaisesRegex(RuntimeError, "human review"):
            inspect_host(self.host)


if __name__ == "__main__":
    unittest.main()
