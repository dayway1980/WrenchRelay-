import importlib.util
from pathlib import Path
import sqlite3
import tempfile
import unittest

spec = importlib.util.spec_from_file_location('backup_rehearsal', Path(__file__).resolve().parents[1] / 'scripts/sqlite_backup_rehearsal.py')
backup = importlib.util.module_from_spec(spec)
spec.loader.exec_module(backup)


class BackupRehearsalTests(unittest.TestCase):
    def setUp(self):
        self.directory = tempfile.TemporaryDirectory()
        self.addCleanup(self.directory.cleanup)
        self.root = Path(self.directory.name)
        self.source = self.root / 'source.sqlite3'
        self.output = self.root / 'backup.sqlite3'

    def create_database(self):
        connection = sqlite3.connect(self.source)
        connection.execute('PRAGMA journal_mode=WAL')
        connection.execute('CREATE TABLE records(id INTEGER PRIMARY KEY, value TEXT)')
        connection.execute("INSERT INTO records(value) VALUES ('synthetic fixture')")
        connection.commit()
        return connection

    def test_committed_wal_data_survives_restore(self):
        connection = self.create_database()
        self.addCleanup(connection.close)
        result = backup.backup_and_rehearse(self.source, self.output)
        self.assertEqual(result['isolated_restore'], 'passed')
        self.assertEqual(result['row_count'], 1)
        with sqlite3.connect(self.output) as restored:
            self.assertEqual(restored.execute('SELECT value FROM records').fetchone()[0], 'synthetic fixture')
        self.assertEqual(self.output.stat().st_mode & 0o777, 0o600)
        self.assertNotIn('synthetic fixture', str(result))

    def test_missing_source_does_not_create_empty_database(self):
        with self.assertRaises(FileNotFoundError):
            backup.backup_and_rehearse(self.source, self.output)
        self.assertFalse(self.source.exists())
        self.assertFalse(self.output.exists())

    def test_empty_database_is_not_a_successful_application_backup(self):
        self.source.touch()
        with self.assertRaises(ValueError):
            backup.backup_and_rehearse(self.source, self.output)
        self.assertFalse(self.output.exists())

    def test_existing_destination_is_preserved(self):
        self.create_database().close()
        self.output.write_bytes(b'keep existing backup')
        with self.assertRaises(FileExistsError):
            backup.backup_and_rehearse(self.source, self.output)
        self.assertEqual(self.output.read_bytes(), b'keep existing backup')

    def test_source_cannot_be_restore_destination(self):
        self.create_database().close()
        before = self.source.read_bytes()
        with self.assertRaises(FileExistsError):
            backup.backup_and_rehearse(self.source, self.source)
        self.assertEqual(self.source.read_bytes(), before)

    def test_corrupt_source_leaves_no_partial_backup(self):
        self.source.write_bytes(b'not a SQLite database')
        with self.assertRaises(sqlite3.DatabaseError):
            backup.backup_and_rehearse(self.source, self.output)
        self.assertFalse(self.output.exists())
        self.assertEqual(list(self.root.glob('.sqlite-snapshot-*')), [])

    def test_foreign_key_violation_blocks_snapshot(self):
        with sqlite3.connect(self.source) as connection:
            connection.executescript('CREATE TABLE parent(id INTEGER PRIMARY KEY); CREATE TABLE child(parent_id INTEGER REFERENCES parent(id)); INSERT INTO child VALUES(99);')
        with self.assertRaises(ValueError):
            backup.backup_and_rehearse(self.source, self.output)
        self.assertFalse(self.output.exists())


if __name__ == '__main__':
    unittest.main()
