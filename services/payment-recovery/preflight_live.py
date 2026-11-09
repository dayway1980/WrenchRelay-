"""Read-only canonical SQLite preflight; optional secure, verified SQLite snapshot.

No Stripe keys, user records or SQLite contents are printed. This does NOT
activate billing, deploy code, or establish Stripe delivery/entitlements.
"""
from __future__ import annotations

import argparse
import ast
import hashlib
from contextlib import closing
import json
import os
from pathlib import Path
import secrets
import shutil
import sqlite3
import sys

REQUIRED_TABLES = frozenset({"users", "billing_accounts", "stripe_events"})


def inspect_host(host_root: Path) -> str:
    source = host_root.resolve(strict=True) / "backend" / "app.py"
    if not source.is_file():
        raise RuntimeError("backend/app.py missing")
    data = source.read_bytes()
    if len(data) > 10_000_000:
        raise RuntimeError("host source unexpectedly large")
    tree = ast.parse(data, filename=str(source))
    declared = {
        node.name for node in tree.body
        if isinstance(node, (ast.FunctionDef, ast.AsyncFunctionDef))
    }
    assigned = {
        target.id for node in tree.body if isinstance(node, (ast.Assign, ast.AnnAssign))
        for target in (node.targets if isinstance(node, ast.Assign) else [node.target])
        if isinstance(target, ast.Name)
    }
    if "current_user" not in declared or not {"app", "DB_PATH"}.issubset(assigned):
        raise RuntimeError("canonical auth/storage contract requires human review")
    return hashlib.sha256(data).hexdigest()


def _connect_readonly(path: Path) -> sqlite3.Connection:
    # SQLite's URI correctly escapes path spaces and special characters.
    return sqlite3.connect(path.as_uri() + "?mode=ro", uri=True, timeout=10)


def check_sqlite(conn: sqlite3.Connection, *, comprehensive: bool = False) -> None:
    tables = {row[0] for row in conn.execute(
        "SELECT name FROM sqlite_master WHERE type='table'"
    )}
    if not REQUIRED_TABLES.issubset(tables):
        raise RuntimeError("canonical database tables missing")
    for name in REQUIRED_TABLES:
        if not list(conn.execute(f'PRAGMA table_info("{name}")')):
            raise RuntimeError("canonical database schema incomplete")
    verdict = conn.execute("PRAGMA integrity_check" if comprehensive else "PRAGMA quick_check").fetchone()
    if not verdict or verdict[0] != "ok":
        raise RuntimeError("database integrity check failed")


def verified_snapshot(db_path: Path, backup_dir: Path) -> Path:
    """Copy using SQLite backup API, validate isolated copy, never change source."""
    backup_dir = backup_dir.resolve(strict=True)
    if not backup_dir.is_dir() or backup_dir.stat().st_mode & 0o077:
        raise RuntimeError("backup directory must exist and be private (0700)")
    if not os.access(backup_dir, os.W_OK):
        raise RuntimeError("backup directory is not writable")
    # Require adequate headroom and avoid placing a new snapshot on the DB itself.
    if backup_dir == db_path.parent:
        raise RuntimeError("backup directory must differ from the live DB directory")
    free = shutil.disk_usage(backup_dir).free
    if free < max(50_000_000, 3 * db_path.stat().st_size):
        raise RuntimeError("insufficient backup free space")
    suffix = secrets.token_hex(6)
    destination = backup_dir / ("wrenchrelay-snapshot-" + suffix + ".sqlite")
    handle = os.open(destination, os.O_WRONLY | os.O_CREAT | os.O_EXCL, 0o600)
    os.close(handle)
    try:
        with closing(_connect_readonly(db_path)) as source:
            with closing(sqlite3.connect(destination)) as target:
                source.backup(target, pages=256, sleep=0.05)
        with closing(_connect_readonly(destination)) as check:
            check_sqlite(check, comprehensive=True)
        return destination
    except BaseException:
        destination.unlink(missing_ok=True)
        raise


def preflight(host_root: Path, db_path: Path, backup_dir: Path | None = None) -> dict[str, object]:
    source_hash = inspect_host(host_root)
    db_path = db_path.resolve(strict=True)
    if not db_path.is_file():
        raise RuntimeError("existing SQLite database required")
    with closing(_connect_readonly(db_path)) as conn:
        check_sqlite(conn)
    result: dict[str, object] = {
        "source_sha256": source_hash,
        "canonical_contract": "source-shape-only; human review still required",
        "sqlite_quick_check": "ok",
        "backup": "not_requested",
        "billing_commissioned": False,
    }
    if backup_dir is not None:
        verified_snapshot(db_path, backup_dir)
        result["backup"] = "created_and_integrity_verified_in_private_directory"
    return result


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--host-root", type=Path, required=True,
                        help="Exact root of running canonical SQLite source, not GitHub MongoDB candidate")
    parser.add_argument("--database", type=Path, required=True,
                        help="Actual SQLite file on existing mounted production volume")
    parser.add_argument("--backup-dir", type=Path,
                        help="Optional existing private 0700 directory with sufficient space")
    args = parser.parse_args()
    try:
        result = preflight(args.host_root, args.database, args.backup_dir)
    except Exception as exc:
        print(json.dumps({"status": "blocked", "error": str(exc), "billing_commissioned": False}))
        return 1
    print(json.dumps({"status": "preflight_ok", **result}, sort_keys=True))
    return 0


if __name__ == "__main__":
    sys.exit(main())
