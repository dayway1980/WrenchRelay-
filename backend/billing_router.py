"""Owner-scoped Stripe trial, checkout, portal, and webhook lifecycle."""

import os
from datetime import datetime, timedelta, timezone

import stripe
from fastapi import APIRouter, HTTPException, Request
from pydantic import BaseModel

from db import db, now_iso
from security import CurrentUser, require_organization

router = APIRouter(prefix="/billing", tags=["billing"])

class CheckoutInput(BaseModel):
    organization_id: str
    plan: str
    origin_url: str

def stripe_client():
    key = os.environ.get("STRIPE_SECRET_KEY")
    if not key:
        raise HTTPException(status_code=503, detail="Billing not configured.")
    stripe.api_key = key

@router.post("/create-checkout-session")
async def checkout(payload: CheckoutInput, user: CurrentUser):
    await require_organization(user, payload.organization_id, "members:read")
    stripe_client()
    org = await db.organizations.find_one({"id": payload.organization_id}, {"_id": 0})
    customer = org.get("stripe_customer_id")
    if not customer:
        created = stripe.Customer.create(email=user["email"], name=org["name"], metadata={"organization_id": payload.organization_id})
        customer = created.id
        await db.organizations.update_one({"id": payload.organization_id}, {"$set": {"stripe_customer_id": customer}})
    price = os.environ.get(f"STRIPE_PRICE_{payload.plan.upper()}")
    if not price:
        raise HTTPException(422, "Choose Starter or Pro.")
    session = stripe.checkout.Session.create(customer=customer, mode="subscription", line_items=[{"price": price, "quantity": 1}], subscription_data={"trial_period_days": 14}, success_url=f"{payload.origin_url}/settings/billing?success=1", cancel_url=f"{payload.origin_url}/settings/billing?cancel=1", metadata={"organization_id": payload.organization_id, "plan": payload.plan})
    return {"url": session.url, "session_id": session.id}

@router.post("/webhooks/stripe")
async def webhook(request: Request):
    body = await request.body()
    secret = os.environ.get("STRIPE_WEBHOOK_SECRET")
    if not secret:
        raise HTTPException(503, "Stripe webhook not configured.")
    stripe.api_key = os.environ.get("STRIPE_SECRET_KEY")
    try:
        event = stripe.Webhook.construct_event(body, request.headers.get("stripe-signature", ""), secret)
    except stripe.SignatureVerificationError as exc:
        raise HTTPException(400, "Invalid signature.") from exc
    obj = event["data"]["object"]
    org_id = obj.get("metadata", {}).get("organization_id")
    if org_id:
        await db.organizations.update_one({"id": org_id}, {"$set": {"subscription.status": obj.get("status", "active"), "subscription.updated_at": now_iso()}})
    return {"received": True}
