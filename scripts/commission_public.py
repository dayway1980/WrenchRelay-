#!/usr/bin/env python3
"""Bounded, GET-only production checks. Passing never commissions billing."""
import concurrent.futures
import datetime
import json
import urllib.error
import urllib.request

BASE = "https://www.wrenchrelayllc.com"
CASES = [("/api/health", 200), ("/api/work-orders", 401),
         ("/api/commissioning-nonexistent", 404), ("/", 200),
         ("/industrial", 200), ("/automotive", 200),
         ("/privacy", 200), ("/terms", 200)]


def check(case):
    path, expected = case
    try:
        try:
            response = urllib.request.urlopen(BASE + path, timeout=20)
        except urllib.error.HTTPError as error:
            response = error
        with response:
            body = response.read(262145)
            passed = response.status == expected and len(body) <= 262144
            detail = "status and response-size checks"
            if path.startswith("/api/"):
                payload = json.loads(body)
                passed = passed and "application/json" in response.headers.get("Content-Type", "")
                if path == "/api/health":
                    passed = passed and payload.get("status") == "ok" and payload.get("database") == "sqlite"
                else:
                    passed = passed and isinstance(payload, dict)
                detail = "JSON API contract; SQLite expected for current live app"
            return {"path": path, "expected": expected, "actual": response.status,
                    "passed": passed, "detail": detail}
    except Exception as error:
        return {"path": path, "passed": False, "error_type": type(error).__name__}


if __name__ == "__main__":
    with concurrent.futures.ThreadPoolExecutor(max_workers=4) as pool:
        results = list(pool.map(check, CASES))
    print(json.dumps({"checked_at_utc": datetime.datetime.now(datetime.timezone.utc).isoformat(),
                      "scope": "GET-only public contracts; no authenticated or payment verification",
                      "billing_commissioned": False, "results": results}, indent=2))
    raise SystemExit(0 if all(row["passed"] for row in results) else 1)
