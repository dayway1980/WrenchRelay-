"""Explicit opt-in integration with backend.app's existing SQLite/auth contract.

Call install(host_module) BEFORE starting Uvicorn, after an isolated restore test.
Do not mount a second DB or deploy this against the MongoDB implementation.
"""
from __future__ import annotations

import asyncio
import logging
import os
import threading
from pathlib import Path
from types import ModuleType
from typing import Any

from fastapi import Header, HTTPException, Request
from fastapi.responses import JSONResponse
from pydantic import BaseModel, ConfigDict

from recovery import BillingError, Recovery, Settings, StripeAPI, secret_value


class CheckoutInput(BaseModel):
    model_config = ConfigDict(extra="forbid")
    price_id: str | None = None


def install(host: ModuleType) -> None:
    app = host.app
    if getattr(app.state, "payment_recovery_installed", False):
        raise RuntimeError("Payment recovery already installed")
    if not callable(getattr(host, "current_user", None)) or not isinstance(getattr(host, "DB_PATH", None), Path):
        raise RuntimeError("Unsupported host authentication/storage contract")
    app.state.payment_recovery_installed = True
    enabled = os.getenv("WR_PAYMENTS_RECOVERY_ENABLED") == "true"
    state: dict[str, Any] = {"recovery": None, "error": "disabled", "last_api_success": 0}
    stop = threading.Event()

    def signing_keys() -> tuple[str, ...]:
        active = secret_value("STRIPE_WEBHOOK_SECRET")
        previous = secret_value("STRIPE_WEBHOOK_SECRET_PREVIOUS")
        return tuple(x for x in (active, previous) if x)

    def configured() -> bool:
        live = os.getenv("STRIPE_LIVEMODE", "true") == "true"
        key = secret_value("STRIPE_SECRET_KEY_LIVE" if live else "STRIPE_SECRET_KEY_TEST")
        prefixes = ("sk_live_", "rk_live_") if live else ("sk_test_", "rk_test_")
        return key.startswith(prefixes) and bool(signing_keys()) and all(k.startswith("whsec_") for k in signing_keys())

    def worker() -> None:
        # Singleton processing is enforced by the DB lease, including across processes.
        while not stop.is_set():
            try:
                recovery: Recovery | None = state["recovery"]
                if recovery:
                    recovery.run_once()
                    if not configured():
                        state["error"] = "credentials_not_configured"
                    else:
                        # This is account authorization, not a payment or a charge.
                        recovery.api.call("GET", "/v1/account")
                        if int(recovery.clock()) - state.get("prices_verified_at", 0) > 300:
                            for price in recovery.settings.prices:
                                obj = recovery.api.call("GET", "/v1/prices/" + price)
                                if (obj.get("active") is not True or obj.get("livemode") is not recovery.settings.livemode
                                        or obj.get("currency") != "usd" or obj.get("type") != "recurring"):
                                    raise BillingError("configured_price_not_ready")
                            state["prices_verified_at"] = int(recovery.clock())
                        state["last_api_success"] = int(recovery.clock())
                        state["error"] = None
            except Exception as exc:
                state["error"] = str(exc) if isinstance(exc, BillingError) else "worker_failure"
                logging.getLogger("wrenchrelay.billing").warning("Payment worker needs recovery: %s", state["error"])
            stop.wait(15)

    def startup() -> None:
        if not enabled:
            return
        try:
            prices = frozenset(x.strip() for x in os.environ["STRIPE_ALLOWED_PRICE_IDS"].split(",") if x.strip())
            mode = os.getenv("STRIPE_LIVEMODE", "true")
            if mode not in ("true", "false"):
                raise BillingError("invalid_mode")
            settings = Settings(os.environ["STRIPE_ACCOUNT_ID"], prices,
                                os.environ["STRIPE_DEFAULT_PRICE_ID"], os.environ["STRIPE_RETURN_ORIGIN"], mode == "true")
            state["recovery"] = Recovery(host.DB_PATH, settings, StripeAPI(settings))
            state["error"] = None
        except Exception:
            state["error"] = "initialization_failed"
            return
        thread = threading.Thread(target=worker, name="wr-billing-recovery", daemon=True)
        state["thread"] = thread
        thread.start()

    def shutdown() -> None:
        stop.set()
        thread = state.get("thread")
        if thread:
            thread.join(timeout=2)

    app.add_event_handler("startup", startup)
    app.add_event_handler("shutdown", shutdown)

    def service() -> Recovery:
        result = state["recovery"]
        if result is None:
            raise HTTPException(503, "Billing recovery is not configured")
        return result

    @app.get("/api/billing/health")
    def billing_health() -> JSONResponse:
        # Public health exposes status only. No account IDs, queue IDs, values or counts.
        recovery: Recovery | None = state["recovery"]
        try:
            health = recovery.health() if recovery else {}
            healthy = bool(enabled and recovery and configured() and state["error"] is None
                           and int(recovery.clock()) - state["last_api_success"] < 120
                           and health.get("oldest_pending_seconds", 0) < 900
                           and health.get("review_required", 0) == 0)
        except Exception:
            healthy = False
        return JSONResponse({"status": "ready" if healthy else "unavailable"}, status_code=200 if healthy else 503,
                            headers={"Cache-Control": "no-store"})

    if not enabled:
        return  # Merely importing this module cannot enable checkout or change fulfillment.

    # Install exact replacements once, retaining every unrelated application route.
    paths = {"/api/checkout", "/api/stripe/webhook", "/api/billing/webhook", "/api/billing/status", "/api/config"}
    original_config = getattr(host, "config", None)
    app.router.routes[:] = [r for r in app.router.routes if getattr(r, "path", None) not in paths]

    @app.post("/api/checkout")
    def checkout(body: CheckoutInput, authorization: str | None = Header(None),
                 idempotency_key: str | None = Header(None, alias="Idempotency-Key")) -> dict[str, str]:
        user = host.current_user(authorization)  # Server-owned identity, not a submitted account ID.
        if not configured():
            raise HTTPException(503, "Billing credentials are not configured")
        try:
            return service().checkout(user["account_id"], body.price_id, idempotency_key)
        except BillingError as exc:
            if str(exc) in ("unapproved_price", "invalid_idempotency_key"):
                raise HTTPException(422, str(exc)) from None
            if str(exc) in ("idempotency_conflict", "subscription_already_present", "existing_subscription_requires_reconciliation", "checkout_expired_new_key_required"):
                raise HTTPException(409, str(exc)) from None
            raise HTTPException(503, "Billing is temporarily unavailable; retry this checkout") from None

    @app.post("/api/stripe/webhook")
    @app.post("/api/billing/webhook")
    async def webhook(request: Request) -> dict[str, bool]:
        raw = bytearray()
        async for chunk in request.stream():
            raw.extend(chunk)
            if len(raw) > 262144:
                raise HTTPException(413, "Webhook too large")
        try:
            accepted = await asyncio.to_thread(service().receive, bytes(raw), request.headers.get("stripe-signature", ""), signing_keys())
        except BillingError as exc:
            status = 503 if str(exc) == "webhook_secret_not_configured" else 400
            raise HTTPException(status, "Webhook could not be accepted") from None
        return {"received": True, "queued": accepted}

    @app.get("/api/billing/status")
    def status(authorization: str | None = Header(None)) -> dict[str, Any]:
        user = host.current_user(authorization)
        return {"account_id": user["account_id"], **service().entitlement(user["account_id"])}

    @app.get("/api/config")
    def config() -> dict[str, Any]:
        response = original_config() if original_config else {}
        recovery: Recovery | None = state["recovery"]
        response["stripe_enabled"] = bool(recovery and configured() and state["error"] is None
                                           and int(recovery.clock()) - state["last_api_success"] < 120)
        return response
