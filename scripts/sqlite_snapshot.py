"""Create a consistent SQLite snapshot without replacing an existing file.

Run on the application host; the output contains private application data.
This does not provide off-host backup or encryption by itself.
"""
import argparse
import os
from pathlib import Path
import sqlite3
import time


def snapshot(source: Path, destination: Path, timeout: float = 60) -> None:
    source = source.resolve(strict=True)
    destination = destination.absolute()
    if not source.is_file():
        raise ValueError("Source must be an existing database file")
    # Reserve the path exclusively, with permissions independent of umask.
    fd = os.open(destination, os.O_CREAT | os.O_EXCL | os.O_WRONLY, 0o600)
    os.close(fd)
    try:
        deadline = time.monotonic() + timeout

        def progress(status, remaining, total):
            if time.monotonic() > deadline:
                raise TimeoutError("Backup deadline exceeded")

        with sqlite3.connect(source.as_uri() + "?mode=ro", uri=True) as src:
            with sqlite3.connect(destination) as dst:
                src.backup(dst, pages=128, progress=progress, sleep=0.1)
                if dst.execute("PRAGMA integrity_check").fetchall() != [("ok",)]:
                    raise RuntimeError("Snapshot failed integrity check")
        with destination.open("rb") as stream:
            os.fsync(stream.fileno())
    except BaseException:
        destination.unlink(missing_ok=True)
        raise


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("source", type=Path)
    parser.add_argument("destination", type=Path)
    args = parser.parse_args()
    snapshot(args.source, args.destination)
    print("Snapshot created and integrity checked; off-host copy still required.")
