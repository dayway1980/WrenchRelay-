"""Owner-scoped Stripe trial, checkout, portal, and webhook lifecycle."""

import os
from datetime import datetime, timedelta, timezone

import stripe
from fastapi import APIRouter, HTTPException, Request
from pydantic import BaseModel

from db import db, now_iso
from security import CurrentUser, require_organization


router = APIRouter(prefix="/billing", tags=["billing"])
PRICES = {"starter": os.environ.get("STRIPE_PRICE_STARTER"), "pro": os.environ.get("STRIPE_PRICE_PRO")}


class CheckoutInput(BaseModel):
    organization_id: str
    plan: str
    origin_url: str


def stripe_client():
    key = os.environ.get("STRIPE_SECRET_KEY")
    if not key:
        raise HTTPException(status_code=503, detail="Billing is not configured.")
    stripe.api_key = key


@router.post("/create-checkout-session")
async def checkout(payload: CheckoutInput, user: CurrentUser):
    await require_organization(user, payload.organization_id, "members:read")
    price = PRICES.get(payload.plan)
    if not price:
        raise HTTPException(status_code=422, detail="Choose Starter or Pro.")
    stripe_client()
    org = await db.organizations.find_one({"id": payload.organization_id}, {"_id": 0})
    customer = org.get("stripe_customer_id")
    if not customer:
        created = stripe.Customer.create(email=user["email"], name=org["name"], metadata={"organization_id": payload.organization_id})
        customer = created.id
        await db.organizations.update_one({"id": payload.organization_id}, {"$set": {"stripe_customer_id": customer}})
    session = stripe.checkout.Session.create(customer=customer, mode="subscription", line_items=[{"price": price, "quantity": max(1, org.get("subscription", {}).get("seat_count", 1))}], subscription_data={"trial_period_days": 14}, success_url=f"{payload.origin_url}/settings/billing?success=1", cancel_url=f"{payload.origin_url}/settings/billing?cancel=1", metadata={"organization_id": payload.organization_id, "plan": payload.plan})
    return {"url": session.url, "session_id": session.id}


@router.post("/create-portal-session")
async def portal(organization_id: str, return_url: str, user: CurrentUser):
    await require_organization(user, organization_id, "members:read")
    stripe_client()
    org = await db.organizations.find_one({"id": organization_id}, {"_id": 0})
    if not org.get("stripe_customer_id"):
        raise HTTPException(status_code=404, detail="No billing customer exists yet.")
    session = stripe.billing_portal.Session.create(customer=org["stripe_customer_id"], return_url=return_url)
    return {"url": session.url}


@router.get("/status")
async def status(organization_id: str, user: CurrentUser):
    await require_organization(user, organization_id, "work_orders:read")
    org = await db.organizations.find_one({"id": organization_id}, {"_id": 0})
    trial_end = org.get("subscription", {}).get("trial_end") or org.get("trial_end")
    if trial_end:
        days = max(0, (datetime.fromisoformat(trial_end) - datetime.now(timezone.utc)).days)
    else:
        days = None
    status_value = org.get("subscription", {}).get("status")
    plan = org.get("subscription", {}).get("plan", "trial")
    if trial_end and days == 0 and status_value == "trialing": plan = "expired"
    return {"plan": plan, "trial_end": trial_end, "days_remaining": days, "stripe_customer_id": org.get("stripe_customer_id"), "subscription_status": status_value}


@router.post("/webhooks/stripe")
async def webhook(request: Request):
    body = await request.body()
    secret = os.environ.get("STRIPE_WEBHOOK_SECRET")
    if not secret:
        raise HTTPException(status_code=503, detail="Stripe webhook signing is not configured.")
    stripe_client()
    try:
        event = stripe.Webhook.construct_event(body, request.headers.get("stripe-signature", ""), secret)
    except stripe.SignatureVerificationError as exc:
        raise HTTPException(status_code=400, detail="Invalid Stripe webhook signature.") from exc
    obj = event["data"]["object"]
    if event["type"] in {"checkout.session.completed", "customer.subscription.updated", "customer.subscription.deleted"}:
        organization_id = obj.get("metadata", {}).get("organization_id")
        if organization_id:
            status_value = obj.get("status", "active")
            await db.organizations.update_one({"id": organization_id}, {"$set": {"subscription.status": status_value, "subscription.stripe_subscription_id": obj.get("subscription", obj.get("id")), "subscription.updated_at": now_iso()}})
    return {"received": True}
