"""Pre-cutover MongoDB verification with no application-data writes."""

import os
import sys

from pymongo import MongoClient
from pymongo.errors import PyMongoError


def main() -> int:
    uri = os.getenv("MONGO_URL") or os.getenv("MONGODB_URI")
    db_name = os.getenv("DB_NAME", "wrenchrelay")
    if not uri:
        print("FAIL: set MONGO_URL or MONGODB_URI", file=sys.stderr)
        return 2

    client = MongoClient(
        uri,
        appname="wrenchrelay-cutover-check",
        connectTimeoutMS=5000,
        serverSelectionTimeoutMS=5000,
        socketTimeoutMS=10000,
        retryReads=True,
        retryWrites=True,
    )
    try:
        hello = client.admin.command("hello")
        client[db_name].command("ping")
        names = sorted(client[db_name].list_collection_names())
    except PyMongoError as exc:
        print(f"FAIL: database verification failed: {type(exc).__name__}", file=sys.stderr)
        return 1
    finally:
        client.close()

    if hello.get("isWritablePrimary") is not True:
        print("FAIL: target has no writable primary", file=sys.stderr)
        return 1
    print(f"PASS: writable primary; database={db_name}; collections={len(names)}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
