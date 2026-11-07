"""Create a new SQLite snapshot and prove it reopens after an isolated restore.

Uses the online backup API, including committed WAL data. Never replaces a
database, imports application code, or prints stored records or credentials.
"""
import argparse
from contextlib import closing
import hashlib
import json
import os
from pathlib import Path
import shutil
import sqlite3
import tempfile


def connect_readonly(path):
    return sqlite3.connect(Path(path).as_uri() + '?mode=ro', uri=True, timeout=10)


def inventory(connection):
    schema = connection.execute(
        "SELECT type, name, tbl_name, sql FROM sqlite_schema "
        "WHERE name NOT LIKE 'sqlite_%' ORDER BY type, name"
    ).fetchall()
    counts = {}
    for kind, name, _, _ in schema:
        if kind == 'table':
            quoted = '"' + name.replace('"', '""') + '"'
            counts[name] = connection.execute('SELECT COUNT(*) FROM ' + quoted).fetchone()[0]
    return {'schema_sha256': hashlib.sha256(json.dumps(schema).encode()).hexdigest(),
            'table_counts': counts}


def verify(connection):
    if connection.execute('PRAGMA integrity_check').fetchall() != [('ok',)]:
        raise ValueError('SQLite integrity check failed')
    if connection.execute('PRAGMA foreign_key_check').fetchone() is not None:
        raise ValueError('SQLite foreign key check failed')
    return inventory(connection)


def backup_and_rehearse(source, destination):
    source = Path(source).resolve(strict=True)
    destination = Path(destination).absolute()
    if not source.is_file():
        raise ValueError('Source must be an existing database file')
    if destination.exists() or destination.is_symlink():
        raise FileExistsError('Destination must be a new file')
    # The caller selects an existing private directory; never create one silently.
    descriptor, temporary = tempfile.mkstemp(prefix='.sqlite-snapshot-', dir=destination.parent)
    os.close(descriptor)  # mkstemp sets mode 0600; SQLite retains it.
    temporary = Path(temporary)
    try:
        with closing(connect_readonly(source)) as src:
            src.execute('BEGIN')
            expected = verify(src)
            if not expected['table_counts']:
                raise ValueError('Source has no application tables')
            with closing(sqlite3.connect(temporary)) as snapshot:
                src.backup(snapshot)
                if verify(snapshot) != expected:
                    raise ValueError('Snapshot inventory does not match source transaction')
            src.rollback()
        with tempfile.TemporaryDirectory(prefix='sqlite-restore-') as directory:
            restored = Path(directory) / 'restored.sqlite3'
            shutil.copyfile(temporary, restored)
            restored.chmod(0o600)
            with closing(connect_readonly(restored)) as connection:
                if verify(connection) != expected:
                    raise ValueError('Isolated restore does not match snapshot')
        with temporary.open('rb') as stream:
            digest = hashlib.file_digest(stream, 'sha256').hexdigest()
        # Atomic creation refuses an existing destination, including a racing writer.
        os.link(temporary, destination)
        return {'status': 'PASS_ON_SUPPLIED_DATABASE', 'backup_sha256': digest,
                'schema_sha256': expected['schema_sha256'],
                'table_count': len(expected['table_counts']),
                'row_count': sum(expected['table_counts'].values()),
                'isolated_restore': 'passed'}
    finally:
        temporary.unlink(missing_ok=True)


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('source', help='Existing SQLite database; opened read-only')
    parser.add_argument('destination', help='New snapshot filename in an existing private directory')
    args = parser.parse_args()
    print(json.dumps(backup_and_rehearse(args.source, args.destination), sort_keys=True))


if __name__ == '__main__':
    main()
