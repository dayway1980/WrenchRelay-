import importlib.util
from pathlib import Path
import sqlite3
import tempfile
import unittest

spec = importlib.util.spec_from_file_location("snapshot", Path(__file__).parents[1] / "scripts/sqlite_snapshot.py")
module = importlib.util.module_from_spec(spec)
spec.loader.exec_module(module)


class SnapshotTests(unittest.TestCase):
    def test_live_wal_snapshot_restores_committed_data_only(self):
        with tempfile.TemporaryDirectory() as folder:
            source, target = Path(folder) / "live.db", Path(folder) / "backup.db"
            with sqlite3.connect(source) as conn:
                conn.execute("PRAGMA journal_mode=WAL")
                conn.execute("CREATE TABLE evidence (value TEXT)")
                conn.execute("INSERT INTO evidence VALUES ('verified')")
                conn.commit()
                conn.execute("INSERT INTO evidence VALUES ('uncommitted')")
                module.snapshot(source, target)
                with sqlite3.connect(target) as restored:
                    self.assertEqual(restored.execute("SELECT value FROM evidence").fetchall(), [("verified",)])
                self.assertEqual(target.stat().st_mode & 0o777, 0o600)

    def test_missing_source_does_not_create_database(self):
        with tempfile.TemporaryDirectory() as folder:
            source, target = Path(folder) / "missing.db", Path(folder) / "backup.db"
            with self.assertRaises(FileNotFoundError):
                module.snapshot(source, target)
            self.assertFalse(source.exists())
            self.assertFalse(target.exists())

    def test_existing_destination_is_never_overwritten(self):
        with tempfile.TemporaryDirectory() as folder:
            source, target = Path(folder) / "live.db", Path(folder) / "backup.db"
            with sqlite3.connect(source):
                pass
            target.write_bytes(b"keep")
            with self.assertRaises(FileExistsError):
                module.snapshot(source, target)
            self.assertEqual(target.read_bytes(), b"keep")

    def test_invalid_source_cleans_up_failed_snapshot(self):
        with tempfile.TemporaryDirectory() as folder:
            source, target = Path(folder) / "bad.db", Path(folder) / "backup.db"
            source.write_bytes(b"not a database")
            with self.assertRaises(sqlite3.DatabaseError):
                module.snapshot(source, target)
            self.assertFalse(target.exists())


if __name__ == "__main__":
    unittest.main()
