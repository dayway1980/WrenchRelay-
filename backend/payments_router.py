"""Stripe subscription checkout for WrenchRelay plans."""

import os

import stripe
from fastapi import APIRouter, HTTPException
from pydantic import BaseModel, HttpUrl

from db import db, now_iso
from security import new_id


router = APIRouter(tags=["payments"])
PRICES = {
    "price_1Tzf4jCpTOQr6SYtzqFAoaJZ": "Starter",
    "price_1TzeuKCpTOQr6SYtqdZugDIN": "Professional",
}


class CheckoutRequest(BaseModel):
    priceId: str
    successUrl: str
    cancelUrl: str


@router.post("/create-checkout-session")
async def create_checkout_session(payload: CheckoutRequest):
    if payload.priceId not in PRICES:
        raise HTTPException(status_code=422, detail="Choose an approved WrenchRelay subscription tier.")
    expected_origin = os.environ["FRONTEND_URL"].rstrip("/")
    if not payload.successUrl.startswith(expected_origin) or not payload.cancelUrl.startswith(expected_origin):
        raise HTTPException(status_code=422, detail="Checkout redirect URLs are invalid.")
    secret_key = os.environ.get("STRIPE_SECRET_KEY_LIVE")
    if not secret_key:
        raise HTTPException(status_code=503, detail="Subscription checkout is not configured yet.")
    stripe.api_key = secret_key
    try:
        session = stripe.checkout.Session.create(
            mode="subscription",
            line_items=[{"price": payload.priceId, "quantity": 1}],
            success_url=payload.successUrl,
            cancel_url=payload.cancelUrl,
            metadata={"plan": PRICES[payload.priceId]},
        )
    except stripe.StripeError as exc:
        raise HTTPException(status_code=502, detail="Stripe could not start checkout. Please try again shortly.") from exc
    record = {"id": new_id(), "session_id": session.id, "price_id": payload.priceId, "plan": PRICES[payload.priceId], "status": "initiated", "payment_status": "pending", "created_at": now_iso(), "updated_at": now_iso()}
    await db.payment_transactions.insert_one(record)
    return {"id": session.id, "url": session.url, "session": {"id": session.id, "url": session.url}}
