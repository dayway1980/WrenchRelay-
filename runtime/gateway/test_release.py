#!/usr/bin/env python3
"""Exercise the complete gateway startup in temporary paths with local mock APIs."""
import argparse
import base64
import hashlib
import http.client
import json
import os
import shlex
import socket
import subprocess
import tempfile
import threading
import time
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer
from pathlib import Path


def free_port():
    with socket.socket() as server:
        server.bind(("127.0.0.1", 0))
        return server.getsockname()[1]


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("--command", default="gateway_start_after.txt")
    parser.add_argument("--caddy", default="./caddy")
    parser.add_argument("--app-js")
    args = parser.parse_args()
    caddy = Path(args.caddy).resolve()
    command = shlex.split(Path(args.command).read_text())
    assert command[:2] == ["sh", "-c"]
    app = Path(args.app_js).read_bytes() if args.app_js else b'console.log("isolated gateway fixture");\n'
    checks = []
    seen = []

    class Backend(BaseHTTPRequestHandler):
        def answer(self):
            seen.append((self.command, self.path))
            status, body = 200, b"isolated upstream fixture"
            content_type = "text/plain"
            if self.path == "/api/health":
                body = b'{"status":"ok","database":"sqlite"}'
                content_type = "application/json"
            elif self.path == "/api/work-orders":
                status, body = 401, b'{"detail":"Not authenticated"}'
                content_type = "application/json"
            elif self.path == "/api/stripe/webhook":
                status, body = 503, b'{"detail":"Stripe webhook is not configured"}'
                content_type = "application/json"
            elif self.path == "/missing-test-route":
                status, body = 404, b"not found"
            self.send_response(status)
            self.send_header("Content-Type", content_type)
            # A stricter policy supplied by an upstream must win over gateway defaults.
            self.send_header("Referrer-Policy", "no-referrer")
            self.end_headers()
            self.wfile.write(body)

        do_GET = answer
        do_POST = answer

        def log_message(self, *_):
            pass

    with tempfile.TemporaryDirectory(prefix="wr-gateway-test-") as temp:
        root = Path(temp)
        shell = command[2]
        for old, target in [
            ("/tmp/public", root / "public"),
            ("/tmp/voice", root / "voice"),
            ("/tmp/Caddyfile", root / "Caddyfile"),
        ]:
            shell = shell.replace(old, str(target))
        shell = shell.replace("exec caddy run --config", shlex.join([str(caddy), "validate", "--config"]))
        fixture = base64.b64encode(app).decode()
        middle = len(fixture) // 2
        env = dict(os.environ, WR_SAVE_GUARDED_APP_JS_00=fixture[:middle],
                   WR_SAVE_GUARDED_APP_JS_01=fixture[middle:])
        subprocess.run(["sh", "-c", shell], env=env, capture_output=True, text=True, check=True, timeout=30)
        assert (root / "voice/app.js").read_bytes() == app
        checks.append("exact frozen app.js preserved")
        config = (root / "Caddyfile").read_text()
        api = ThreadingHTTPServer(("127.0.0.1", 0), Backend)
        thread = threading.Thread(target=api.serve_forever, daemon=True)
        thread.start()
        port = free_port()
        config = config.replace(":8000 {", f"http://:{port} {{\n  bind 127.0.0.1", 1)
        config = config.replace("wrenchrelay-production.railway.internal:8080", f"127.0.0.1:{api.server_port}")
        config = config.replace("wrenchrelay-recovery.railway.internal:8080", f"127.0.0.1:{api.server_port}")
        (root / "Caddyfile.local").write_text(config)
        log = (root / "caddy.log").open("w")
        process = subprocess.Popen([str(caddy), "run", "--config", str(root / "Caddyfile.local"),
                                    "--adapter", "caddyfile"], stdout=log, stderr=log)

        def request(path, method="GET"):
            connection = http.client.HTTPConnection("127.0.0.1", port, timeout=3)
            try:
                connection.request(method, path, body=b"{}" if method == "POST" else None,
                                   headers={"Host": "www.wrenchrelayllc.com"})
                result = connection.getresponse()
                return result.status, dict(result.getheaders()), result.read()
            finally:
                connection.close()

        def verify_headers(headers, upstream=False):
            headers = {key.lower(): value for key, value in headers.items()}
            assert headers.get("x-content-type-options") == "nosniff", headers
            assert headers.get("x-frame-options") == "DENY", headers
            assert headers.get("referrer-policy") == ("no-referrer" if upstream else "strict-origin-when-cross-origin"), headers
            assert headers.get("x-wrenchrelay-release") == "gateway-20261029-r1", headers

        try:
            for _ in range(100):
                try:
                    health = request("/health")
                    if health[0] == 200 and health[2] == b"voice-v6-health":
                        break
                except (OSError, http.client.HTTPException):
                    time.sleep(0.05)
            else:
                raise RuntimeError("Local gateway failed to start: " + (root / "caddy.log").read_text()[-2000:])
            for path in ["/account-deletion", "/account-deletion/", "/delete-account/"]:
                status, headers, _ = request(path)
                assert status == 308, (path, status)
                assert headers.get("Location") == "/delete-account", headers
                verify_headers(headers)
                checks.append(path + " redirects to existing deletion page")
            for path, marker in [
                ("/delete-account", b"Delete your WrenchRelay account"),
                ("/privacy-android", b"WrenchRelay Industrial Android Privacy"),
                ("/industrial", b"Keep the knowledge"),
                ("/automotive", b"Automotive"),
                ("/hybrid-wheel-press", b"Hybrid Wheel Press"),
                ("/robots.txt", b"Sitemap:"),
                ("/sitemap.xml", b"<urlset"),
                ("/health", b"voice-v6-health"),
                ("/voice-version", b"voice-session-v8-play-ready"),
            ]:
                status, headers, body = request(path)
                assert status == 200 and marker in body, (path, status)
                verify_headers(headers)
                checks.append(path + " preserved with headers")
            status, headers, served = request("/app.js")
            assert status == 200 and served == app
            verify_headers(headers)
            checks.append("served app.js byte parity")
            for path, expected in [("/", 200), ("/privacy", 200), ("/api/health", 200),
                                   ("/api/work-orders", 401), ("/missing-test-route", 404)]:
                status, headers, _ = request(path)
                assert status == expected, (path, status)
                verify_headers(headers, upstream=True)
                checks.append(path + " upstream semantics preserved")
            status, headers, _ = request("/api/billing/webhook", "POST")
            assert status == 503, status
            assert ("POST", "/api/stripe/webhook") in seen
            verify_headers(headers, upstream=True)
            checks.append("legacy webhook rewrite and unconfigured denial preserved")
        finally:
            process.terminate()
            try:
                process.wait(timeout=5)
            except subprocess.TimeoutExpired:
                process.kill()
                process.wait()
            api.shutdown()
            api.server_close()
            log.close()
    result = {
        "passed": len(checks),
        "checks": checks,
        "frozen_js_sha256": hashlib.sha256(app).hexdigest(),
        "production_data_used": False,
    }
    print(json.dumps(result, indent=2))


if __name__ == "__main__":
    main()
