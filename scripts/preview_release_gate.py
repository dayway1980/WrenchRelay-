#!/usr/bin/env python3
"""Read-only, fail-closed WrenchRelay PREVIEW release probe.

Usage:
    python scripts/preview_release_gate.py --self-test
    python scripts/preview_release_gate.py --url https://YOUR-PREVIEW.vercel.app

The probe sends only unauthenticated GET requests to a vercel.app preview.
It never registers a user, charges a card, submits a webhook, follows redirects,
stores a cookie, or changes production. A green probe is NOT a release approval:
authenticated end-to-end and Stripe-signed test-mode checks remain mandatory.
"""
import argparse
import json
import sys
import unittest
from urllib.error import HTTPError, URLError
from urllib.parse import urlsplit
from urllib.request import HTTPRedirectHandler, Request, build_opener

READ_ONLY_PATHS = (
    "/__bridge/railway-health",
    "/api/health/live",
    "/api/health/ready",
    "/api/config",
    "/api/me",
    "/api/work-orders",
    "/signup",
    "/login",
    "/privacy",
    "/delete-account",
)
MAX_RESPONSE_BYTES = 4096


def preview_base(raw: str) -> str:
    """Accept only a single HTTPS preview hostname. Never probe production."""
    p = urlsplit(raw.strip())
    host = (p.hostname or "").lower()
    if (p.scheme != "https" or not host.endswith(".vercel.app")
            or host == "vercel.app" or p.username or p.password
            or p.port not in (None, 443) or p.path not in ("", "/")
            or p.query or p.fragment or any(c in host for c in "\\@")):
        raise ValueError("Expected a bare https://<deployment>.vercel.app preview URL")
    return "https://" + host


class NoRedirects(HTTPRedirectHandler):
    def redirect_request(self, request, fp, code, msg, headers, newurl):
        return None


def get_read_only(base: str, path: str, opener=None) -> dict:
    opener = opener or build_opener(NoRedirects())
    request = Request(
        base + path,
        method="GET",
        headers={"Accept": "application/json, text/html;q=0.8",
                 "User-Agent": "WrenchRelay-Preview-ReadOnly-Gate/1.0"},
    )
    try:
        response = opener.open(request, timeout=10)
    except HTTPError as exc:
        response = exc
    except (URLError, TimeoutError, OSError) as exc:
        return {"path": path, "status": None, "kind": "network-error",
                "detail": type(exc).__name__}
    with response:
        status = response.status
        ctype = response.headers.get("Content-Type", "").lower()
        via = response.headers.get("Via", "")
        raw = response.read(MAX_RESPONSE_BYTES)
    kind = "html" if "text/html" in ctype else "json" if "json" in ctype else "other"
    body = {}
    if kind == "json":
        try:
            body = json.loads(raw.decode("utf-8", errors="replace"))
        except (json.JSONDecodeError, UnicodeDecodeError):
            body = {}
    return {"path": path, "status": status, "kind": kind, "body": body, "via": via}


def classify(results: dict) -> dict:
    """Differentiate available infrastructure from authentic customer readiness."""
    bridge = results["/__bridge/railway-health"]
    ready = results["/api/health/ready"]
    live = results["/api/health/live"]
    config = results["/api/config"]
    protected = [results["/api/me"], results["/api/work-orders"]]
    html_pages = [results[p] for p in ("/signup", "/login", "/privacy", "/delete-account")]
    bridge_ok = (bridge["status"] == 200
                 and bridge.get("body", {}).get("status") == "ok"
                 and "caddy" in bridge.get("via", "").lower())
    ready_ok = (ready["status"] == 200
                and ready.get("body", {}).get("database") == "ok")
    protections_ok = all(p["status"] in (401, 403) for p in protected)
    pages_shell = all(p["status"] == 200 and p["kind"] == "html" for p in html_pages)
    flags = config.get("body", {}) if config["status"] == 200 else {}
    return {
        "health_bridge": "PASS" if bridge_ok else "BLOCKED",
        "candidate_liveness": "PASS" if live["status"] == 200 else "BLOCKED",
        "candidate_database_readiness": "PASS" if ready_ok else "BLOCKED",
        "unauthenticated_route_protection": "PASS" if protections_ok else "BLOCKED",
        "html_route_shells": "LOAD_ONLY_NOT_SIGNUP_PROOF" if pages_shell else "BLOCKED",
        "candidate_google_configured": flags.get("google_enabled") is True,
        "candidate_stripe_configured": flags.get("stripe_enabled") is True,
        "read_only_smoke_passed": bridge_ok and ready_ok and protections_ok and pages_shell,
        "commercial_release_approved": False,
        "still_required": [
            "Authenticated registration/login, cookie/session and tenant-isolation tests",
            "Stripe account identity, signed sandbox webhook and exactly-once entitlement",
            "Approved tax treatment and customer offer before charging",
            "Voice, Automotive and Industrial real workflow acceptance",
            "Reviewed production diff, tested rollback and explicit owner approval",
        ],
    }


class SelfTests(unittest.TestCase):
    def test_only_preview_hostname_allowed(self):
        self.assertEqual(preview_base("https://abc.vercel.app/"), "https://abc.vercel.app")
        for value in ("http://abc.vercel.app", "https://vercel.app",
                      "https://abc.vercel.app.attacker.example",
                      "https://www.wrenchrelayllc.com",
                      "https://abc.vercel.app/api", "https://abc.vercel.app/?x=1",
                      "https://alice:pw@abc.vercel.app"):
            with self.subTest(value=value), self.assertRaises(ValueError):
                preview_base(value)

    def test_fail_closed_on_unconfigured_auth_and_database(self):
        sample = {p: {"status": 200, "kind": "html", "body": {}, "via": ""}
                  for p in READ_ONLY_PATHS}
        sample["/__bridge/railway-health"].update(
            kind="json", via="1.1 Caddy", body={"status": "ok", "database": "sqlite"})
        sample["/api/health/live"].update(kind="json")
        sample["/api/health/ready"].update(
            status=503, kind="json",
            body={"detail": {"database": "not_configured"}})
        sample["/api/config"].update(
            kind="json", body={"stripe_enabled": False, "google_enabled": False})
        for p in ("/api/me", "/api/work-orders"):
            sample[p].update(status=503, kind="json",
                             body={"detail": "Authentication is not configured"})
        result = classify(sample)
        self.assertEqual(result["health_bridge"], "PASS")
        self.assertEqual(result["candidate_database_readiness"], "BLOCKED")
        self.assertEqual(result["unauthenticated_route_protection"], "BLOCKED")
        self.assertFalse(result["read_only_smoke_passed"])
        self.assertFalse(result["commercial_release_approved"])

    def test_never_certifies_commercial_release(self):
        sample = {p: {"status": 200, "kind": "html", "body": {}, "via": ""}
                  for p in READ_ONLY_PATHS}
        sample["/__bridge/railway-health"].update(
            kind="json", via="1.1 Caddy", body={"status": "ok"})
        sample["/api/health/ready"].update(kind="json", body={"database": "ok"})
        sample["/api/config"].update(kind="json")
        for p in ("/api/me", "/api/work-orders"):
            sample[p].update(status=401, kind="json")
        result = classify(sample)
        self.assertTrue(result["read_only_smoke_passed"])
        self.assertFalse(result["commercial_release_approved"])


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--url", help="HTTPS URL of an isolated Vercel preview")
    parser.add_argument("--self-test", action="store_true",
                        help="Run offline tests only; never make network requests")
    args = parser.parse_args()
    if args.self_test:
        suite = unittest.defaultTestLoader.loadTestsFromTestCase(SelfTests)
        return 0 if unittest.TextTestRunner(verbosity=2).run(suite).wasSuccessful() else 1
    if not args.url:
        parser.error("--url is required unless --self-test is used")
    try:
        base = preview_base(args.url)
    except ValueError as exc:
        parser.error(str(exc))
    results = {p: get_read_only(base, p) for p in READ_ONLY_PATHS}
    report = {"target": base, "paths": [
        {"path": p, "status": results[p]["status"], "kind": results[p]["kind"]}
        for p in READ_ONLY_PATHS
    ], "decision": classify(results)}
    print(json.dumps(report, indent=2, sort_keys=True))
    return 0 if report["decision"]["read_only_smoke_passed"] else 1


if __name__ == "__main__":
    sys.exit(main())
