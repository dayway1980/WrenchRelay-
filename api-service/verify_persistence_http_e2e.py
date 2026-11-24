"""Isolated WrenchRelay persistence acceptance test.

Runs ONLY against MongoDB on localhost supplied by the GitHub Actions job.
Exercises the real FastAPI app over HTTP with dummy accounts and test notes.
No live keys, no production data, no emails and no payment or AI calls.
"""
import json
import os
import signal
import subprocess
import sys
import time
from pathlib import Path

import httpx
from pymongo import MongoClient

BASE = "http://127.0.0.1:18765"
DB_NAME = "wrenchrelay_ci_persistence_isolated"
MONGO = "mongodb://127.0.0.1:27017"


def checked(condition, description):
    if not condition:
        raise AssertionError(description)
    print("PASS:", description, flush=True)


def start_api():
    env = os.environ.copy()
    env.update({
        "MONGO_URL": MONGO,
        "DB_NAME": DB_NAME,
        "JWT_SECRET": "ci-only-fake-jwt-key-for-local-qa-20261124",
        "VERCEL_ENV": "",
        "WRENCHRELAY_REALTIME_ENABLED": "false",
        "WRENCHRELAY_REALTIME_BUDGET_APPROVED": "false",
        "OPENAI_API_KEY": "",
        "STRIPE_SECRET_KEY": "",
        "GOOGLE_CLIENT_ID": "",
        "FRONTEND_URL": BASE,
        "CORS_ORIGINS": BASE,
        "PYTHONUNBUFFERED": "1",
        "WR_ISOLATED_QA": "true",
        "WR_QA_ACCESS_TOKEN": "CI-ONLY-NO-REAL-SECRETS-VOICE-QA",
    })
    path = Path(__file__).resolve().parent
    proc = subprocess.Popen(
        [sys.executable, "-m", "uvicorn", "main:app", "--host", "127.0.0.1", "--port", "18765", "--no-access-log"],
        env=env, cwd=path, stdout=subprocess.PIPE, stderr=subprocess.STDOUT,
        start_new_session=True,
    )
    for _ in range(90):
        if proc.poll() is not None:
            out = proc.stdout.read().decode("utf-8", errors="replace") if proc.stdout else ""
            raise RuntimeError("API exited before startup: " + out[-1000:])
        try:
            r = httpx.get(BASE + "/api/health", timeout=0.8)
            if r.status_code == 200 and r.json().get("database") == "ok":
                return proc
        except (httpx.RequestError, ValueError):
            pass
        time.sleep(0.25)
    terminate(proc)
    raise RuntimeError("Local staging API did not become DB-ready")


def terminate(proc):
    if not proc or proc.poll() is not None:
        return
    try:
        os.killpg(proc.pid, signal.SIGTERM)
    except ProcessLookupError:
        pass
    try:
        proc.communicate(timeout=8)
    except subprocess.TimeoutExpired:
        os.killpg(proc.pid, signal.SIGKILL)
        proc.communicate(timeout=4)


def main():
    # Only localhost MongoDB is supported. Do not accidentally test any remote DB.
    checked(os.getenv("WR_QA_ALLOW_LOCAL_MONGO") == "1",
            "local-only test opted in explicitly")
    checked(os.getenv("MONGO_URL") in (None, "", MONGO),
            "no production MongoDB URL can leak into the test process")
    client = MongoClient(MONGO, serverSelectionTimeoutMS=2500)
    client.admin.command("ping")
    db = client[DB_NAME]
    checked(not db.list_collection_names(), "isolated database starts empty")
    proc = None
    try:
        proc = start_api()
        checked(httpx.get(BASE + "/api/me").status_code == 403,
                "QA boundary rejects requests without its access secret")
        with httpx.Client(base_url=BASE, timeout=12, headers={"X-WR-QA-Access": "CI-ONLY-NO-REAL-SECRETS-VOICE-QA"}) as owner, httpx.Client(base_url=BASE, timeout=12, headers={"X-WR-QA-Access": "CI-ONLY-NO-REAL-SECRETS-VOICE-QA"}) as other:
            checked(owner.get("/api/work-orders").status_code == 401,
                    "anonymous saved-work-order read rejected")
            checked(owner.get("/api/me").status_code == 401, "anonymous identity rejected")
            checked(owner.post("/api/realtime/client-secret", json={"mode":"industrial", "language":"English"}, headers={"Origin": BASE}).status_code == 503,
                    "anonymous Realtime blocked by private QA provider hold")
            a = owner.post("/api/auth/register", json={
                "email": "qa-owner@example.com",
                "name": "CI Owner Test",
                "password": "Qa-Only-Strong-Password-2246!",
            })
            checked(a.status_code == 200, f"fictional owner registered without checkout (HTTP {a.status_code})")
            if a.status_code == 200:
                owner.headers["Authorization"] = "Bearer " + a.json()["token"]
            checked(owner.get("/api/me").json().get("email") == "qa-owner@example.com",
                    "signed-in owner session validated")
            checked(owner.post("/api/auth/register", json={"email":"qa-third@example.com","password":"strong-pass-qa-just-test"}, headers={"X-WR-QA-Access":"incorrect"}).status_code == 403,
                    "wrong QA access secret cannot register accounts")
            checked(owner.get("/api/config").json().get("realtime_voice_enabled") is False,
                    "no-cost Realtime remains disabled by default")
            checked(owner.post("/api/realtime/client-secret", json={"mode":"industrial", "language":"English"}, headers={"Origin": BASE}).status_code == 503,
                    "authenticated voice request fails closed when flags are off")
            record = {
                "mode": "industrial",
                "narrative": "QA TEST ONLY: observations unverified; no repairs performed.",
                "data": {
                    "work_order_number": "QA-CI-001",
                    "asset": "Fictional conveyor C-17",
                    "complaint": "QA TEST ONLY: drive periodically stops",
                    "observed_condition": "QA TEST ONLY: no live equipment observed",
                    "diagnostics": "QA TEST ONLY: measured values unknown",
                    "safety_loto": "QA TEST ONLY: isolation not performed; no work authorized",
                    "corrective_action": "QA TEST ONLY: none",
                    "parts_used": "QA TEST ONLY: none",
                    "verification": "QA TEST ONLY: not tested; outcome unknown",
                },
            }
            s = owner.post("/api/work-orders", json=record)
            checked(s.status_code == 200, "saved fictional order via authenticated API")
            saved = s.json()
            checked(saved.get("id") and saved.get("data", {}).get("asset") == record["data"]["asset"],
                    "create response contains unique ID and exact fictional asset")
            r = owner.get("/api/work-orders")
            checked(r.status_code == 200 and any(x["id"] == saved["id"] for x in r.json()),
                    "owner retrieves saved order before restart")
            second = other.post("/api/auth/register", json={
                "email": "qa-other@example.com",
                "name": "CI Other Tenant",
                "password": "Qa-Other-Strong-Password-2246!",
            })
            checked(second.status_code == 200, f"second fictional tenant registered (HTTP {second.status_code})")
            if second.status_code == 200:
                other.headers["Authorization"] = "Bearer " + second.json()["token"]
            list_other = other.get("/api/work-orders")
            checked(list_other.status_code == 200 and list_other.json() == [],
                    "other tenant cannot read owner's saved work order")
            checked(owner.post("/api/auth/logout").status_code == 200, "owner logged out")
            owner.headers.pop("Authorization", None)  # Bearer tokens are independent of logout cookies
            checked(owner.get("/api/work-orders").status_code == 401,
                    "owner read rejected after logout")
        terminate(proc)
        proc = None
        # DB container stays alive while the actual API process is restarted.
        proc = start_api()
        with httpx.Client(base_url=BASE, timeout=12, headers={"X-WR-QA-Access": "CI-ONLY-NO-REAL-SECRETS-VOICE-QA"}) as logged_back_in:
            login = logged_back_in.post("/api/auth/login", json={
                "email": "qa-owner@example.com",
                "password": "Qa-Only-Strong-Password-2246!",
            })
            checked(login.status_code == 200, f"fictional owner logs in after process restart (HTTP {login.status_code})")
            if login.status_code == 200:
                logged_back_in.headers["Authorization"] = "Bearer " + login.json()["token"]
            resp = logged_back_in.get("/api/work-orders")
            checked(resp.status_code == 200, "saved orders list after restart returns 200")
            matches = [x for x in resp.json() if x.get("id") == saved["id"]]
            checked(len(matches) == 1, "saved work order survives actual backend restart")
            checked(matches[0]["data"]["verification"] == record["data"]["verification"],
                    "unverified test outcome persisted without alteration")
            checked(matches[0]["data"]["safety_loto"] == record["data"]["safety_loto"],
                    "safety/LOTO uncertainty persisted without alteration")
        print("ISOLATED AUTHENTICATED HTTP PERSISTENCE E2E PASS", flush=True)
    finally:
        terminate(proc)
        # This is a CI-only temporary DB, never customer production.
        client.drop_database(DB_NAME)
        client.close()


if __name__ == "__main__":
    main()
