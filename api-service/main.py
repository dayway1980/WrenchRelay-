import os
import uuid
from datetime import datetime, timedelta, timezone
from typing import Optional

from fastapi import FastAPI, HTTPException, Depends, Header, Request, Response
from fastapi.middleware.cors import CORSMiddleware
from pydantic import BaseModel, EmailStr, Field
from jose import jwt, JWTError
from passlib.context import CryptContext
from pymongo import MongoClient
from openai import OpenAI

try:
    import stripe
except Exception:  # pragma: no cover
    stripe = None

try:
    from google.oauth2 import id_token as google_id_token
    from google.auth.transport import requests as google_requests
except Exception:  # pragma: no cover
    google_id_token = None
    google_requests = None

APP_NAME = "WrenchRelay"
APP_VERSION = "2.0.0"
JWT_SECRET = os.getenv("JWT_SECRET", "")
JWT_ALG = "HS256"
MONGO_URL = os.getenv("MONGO_URL") or os.getenv("MONGODB_URI")
DB_NAME = os.getenv("DB_NAME", "wrenchrelay")
OPENAI_API_KEY = os.getenv("OPENAI_API_KEY", "")
OPENAI_BASE_URL = os.getenv("OPENAI_BASE_URL") or None
OPENAI_MODEL = os.getenv("OPENAI_MODEL", "gpt-4o-mini")
GOOGLE_CLIENT_ID = os.getenv("GOOGLE_CLIENT_ID", "")
FRONTEND_URL = os.getenv("FRONTEND_URL", "https://www.wrenchrelay.com").rstrip("/")
LEGAL_ENTITY_NAME = os.getenv("LEGAL_ENTITY_NAME", "God's Plan LLC")
LEGAL_EMAIL = os.getenv("LEGAL_EMAIL", "support@wrenchrelay.com")
BRAVA_DOMAIN = (os.getenv("BRAVA_DOMAIN") or os.getenv("BRAVA_EMAIL_DOMAIN") or "bravatile.com").lower()
BRAVA_LIFETIME_EMAILS = {x.strip().lower() for x in os.getenv("BRAVA_LIFETIME_EMAILS", "").split(",") if x.strip()}
TRIAL_DAYS = int(os.getenv("TRIAL_DAYS", "14"))
SESSION_COOKIE = "wrenchrelay_session"

app = FastAPI(title="WrenchRelay API", version=APP_VERSION)
origins = [x.strip() for x in os.getenv("CORS_ORIGINS", "").split(",") if x.strip()]
if not origins:
    origins = [
        "https://wrenchrelay.com",
        "https://www.wrenchrelay.com",
        "https://app.wrenchrelay.com",
        "https://industrial.wrenchrelay.com",
        "https://automotive.wrenchrelay.com",
    ]
app.add_middleware(
    CORSMiddleware,
    allow_origins=origins,
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

pwd = CryptContext(schemes=["bcrypt"], deprecated="auto")
_client = MongoClient(MONGO_URL, serverSelectionTimeoutMS=3000) if MONGO_URL else None
_db = _client[DB_NAME] if _client else None

PERSONALITIES = {
    "straight-shooter": "Direct, concise, practical, no fluff. Give the next useful action first.",
    "coach": "Supportive maintenance coach. Explain reasoning briefly and teach while helping.",
    "old-school-tech": "Experienced shop-floor veteran tone. Practical and grounded, never reckless.",
    "calm-expert": "Calm, measured expert. Reduce noise, separate facts from hypotheses.",
    "controls-nerd": "Controls specialist. Emphasize PLC logic, I/O, networks, drives and sensors when relevant.",
    "reliability-pro": "Reliability engineer mindset. Emphasize repeat failures, evidence, PM/PdM and prevention.",
    "safety-first": "Safety-focused technician. Call out energy-control and qualified-person boundaries clearly.",
    "detective": "Troubleshooting detective. Build and eliminate hypotheses from evidence.",
    "shop-floor": "Friendly, plain-language shop-floor communicator. Easy to read during a breakdown.",
    "concise": "Extremely concise. Short bullets and only decision-relevant information.",
    "teacher": "Explain technical concepts in accessible language without talking down to the user.",
    "commander": "Incident-response style: stabilize, verify, isolate, act, test, document.",
}

PLAN_LIMITS = {"free": 20, "starter": 150, "pro": 1500, "pro_lifetime": 999999}


class Register(BaseModel):
    email: EmailStr
    password: str = Field(min_length=8)
    name: str = ""


class Login(BaseModel):
    email: EmailStr
    password: str


class GoogleCredential(BaseModel):
    credential: str


class AIRequest(BaseModel):
    text: str = Field(min_length=1, max_length=20000)
    language: str = "English"
    asset: str = ""
    context: str = ""
    mode: str = "industrial"
    personality: str = "straight-shooter"


class WorkOrder(BaseModel):
    work_order_number: str = ""
    asset: str = ""
    area: str = ""
    complaint: str = ""
    observed_condition: str = ""
    safety_loto: str = ""
    diagnostics: str = ""
    root_cause: str = ""
    corrective_action: str = ""
    parts_used: str = ""
    verification: str = ""
    downtime_minutes: Optional[int] = None
    follow_up: str = ""
    technician: str = ""


class SaveWorkOrder(BaseModel):
    data: WorkOrder
    narrative: str = ""
    mode: str = "industrial"


class CheckoutRequest(BaseModel):
    plan: str


def utcnow():
    return datetime.now(timezone.utc)


def is_brava(email: str) -> bool:
    email = email.lower().strip()
    return email in BRAVA_LIFETIME_EMAILS or email.endswith("@" + BRAVA_DOMAIN)


def token_for(email: str):
    if not JWT_SECRET:
        raise HTTPException(503, "Authentication is not configured")
    return jwt.encode({"sub": email.lower(), "exp": utcnow() + timedelta(days=7)}, JWT_SECRET, algorithm=JWT_ALG)


def current_user(request: Request, authorization: Optional[str] = Header(default=None)):
    if not JWT_SECRET:
        raise HTTPException(503, "Authentication is not configured")
    token = request.cookies.get(SESSION_COOKIE)
    if not token and authorization and authorization.startswith("Bearer "):
        token = authorization[7:]
    if not token:
        raise HTTPException(401, "Not authenticated")
    try:
        payload = jwt.decode(token, JWT_SECRET, algorithms=[JWT_ALG])
        return payload["sub"]
    except JWTError:
        raise HTTPException(401, "Invalid or expired token")



def set_session(response: Response, token: str):
    response.set_cookie(
        SESSION_COOKIE, token, httponly=True, secure=True, samesite="lax",
        max_age=7*24*3600, path="/"
    )

def require_db():
    if _db is None:
        raise HTTPException(503, "Database is not configured")
    return _db


def entitlement_for(user_doc: dict) -> dict:
    email = user_doc.get("email", "")
    plan = user_doc.get("plan", "free")
    if is_brava(email):
        plan = "pro_lifetime"
    created = user_doc.get("created_at") or utcnow()
    if getattr(created, "tzinfo", None) is None:
        created = created.replace(tzinfo=timezone.utc)
    trial_end = created + timedelta(days=TRIAL_DAYS)
    trial_active = utcnow() < trial_end
    effective = "pro" if plan == "free" and trial_active else plan
    return {
        "plan": plan,
        "effective_plan": effective,
        "brava_lifetime": is_brava(email),
        "trial_active": trial_active,
        "trial_end": trial_end.isoformat(),
        "ai_limit": PLAN_LIMITS.get(effective, PLAN_LIMITS["free"]),
    }


def user_doc(email: str) -> dict:
    db = require_db()
    u = db.users.find_one({"email": email.lower()})
    if not u:
        raise HTTPException(404, "Account not found")
    if is_brava(email) and u.get("plan") != "pro_lifetime":
        db.users.update_one({"email": email.lower()}, {"$set": {"plan": "pro_lifetime", "brava_lifetime": True}})
        u["plan"] = "pro_lifetime"
        u["brava_lifetime"] = True
    return u


def month_key():
    return utcnow().strftime("%Y-%m")


def consume_ai(email: str):
    db = require_db()
    u = user_doc(email)
    ent = entitlement_for(u)
    key = month_key()
    usage = u.get("usage", {})
    count = int(usage.get(key, 0))
    if count >= ent["ai_limit"]:
        raise HTTPException(402, "AI usage limit reached for this plan")
    db.users.update_one({"email": email.lower()}, {"$inc": {f"usage.{key}": 1}})


def llm(prompt: str, personality: str = "straight-shooter") -> str:
    if not OPENAI_API_KEY:
        raise HTTPException(503, "AI is not configured")
    kwargs = {"api_key": OPENAI_API_KEY}
    if OPENAI_BASE_URL:
        kwargs["base_url"] = OPENAI_BASE_URL
    client = OpenAI(**kwargs)
    style = PERSONALITIES.get(personality, PERSONALITIES["straight-shooter"])
    system = (
        "You are WrenchRelay, an industrial and automotive maintenance documentation and troubleshooting assistant. "
        "Never invent measurements, parts, root causes, safety steps, machine states, test results, or repairs. "
        "Never advise bypassing guards, interlocks, LOTO, arc-flash boundaries, safety systems, emissions controls, or other safeguards. "
        "Clearly separate known facts, hypotheses, and recommended checks. "
        f"Communication style: {style}"
    )
    r = client.chat.completions.create(
        model=OPENAI_MODEL,
        temperature=0.2,
        messages=[{"role": "system", "content": system}, {"role": "user", "content": prompt}],
    )
    return r.choices[0].message.content or ""


def mode_context(mode: str) -> str:
    if mode.lower() == "automotive":
        return (
            "AUTOMOTIVE MODE: Think like a professional automotive diagnostic assistant. Emphasize complaint verification, "
            "DTCs/freeze-frame when provided, scan data, power/ground, wiring, sensors/actuators, mechanical condition, service information, "
            "road-test verification, torque/specification lookup boundaries, and safe lifting/airbag/high-voltage EV procedures."
        )
    return (
        "INDUSTRIAL MODE: Think like an industrial maintenance assistant. Emphasize machine state, PLC/I-O, drives, sensors, electrical, "
        "mechanical, pneumatic/hydraulic, process conditions, guarding, LOTO, qualified-person boundaries, and return-to-service verification."
    )


@app.middleware("http")
async def security_headers(request: Request, call_next):
    response = await call_next(request)
    response.headers.setdefault("X-Content-Type-Options", "nosniff")
    response.headers.setdefault("X-Frame-Options", "DENY")
    response.headers.setdefault("Referrer-Policy", "strict-origin-when-cross-origin")
    response.headers.setdefault("Permissions-Policy", "camera=(), geolocation=(), payment=(self), microphone=(self)")
    response.headers.setdefault("Strict-Transport-Security", "max-age=31536000; includeSubDomains")
    return response


@app.get("/api/health")
def health():
    db_ok = False
    if _client:
        try:
            _client.admin.command("ping")
            db_ok = True
        except Exception:
            db_ok = False
    return {
        "status": "ok",
        "service": "wrenchrelay",
        "version": APP_VERSION,
        "database": "ok" if db_ok else ("unavailable" if MONGO_URL else "not_configured"),
    }


@app.get("/api/config")
def config():
    return {
        "app_name": APP_NAME,
        "version": APP_VERSION,
        "google_client_id": GOOGLE_CLIENT_ID,
        "google_enabled": bool(GOOGLE_CLIENT_ID and google_id_token),
        "stripe_enabled": bool((os.getenv("STRIPE_SECRET_KEY_LIVE") or os.getenv("STRIPE_SECRET_KEY")) and stripe),
        "legal_entity": LEGAL_ENTITY_NAME,
        "legal_email": LEGAL_EMAIL,
        "personalities": [{"id": k, "name": k.replace("-", " ").title(), "description": v} for k, v in PERSONALITIES.items()],
        "brava_domain": BRAVA_DOMAIN,
    }


@app.post("/api/auth/register")
def register(body: Register, response: Response):
    db = require_db()
    email = body.email.lower()
    if db.users.find_one({"email": email}):
        raise HTTPException(409, "Account already exists")
    plan = "pro_lifetime" if is_brava(email) else "free"
    doc = {
        "email": email,
        "name": body.name.strip(),
        "password_hash": pwd.hash(body.password),
        "auth_method": "password",
        "plan": plan,
        "brava_lifetime": is_brava(email),
        "created_at": utcnow(),
        "usage": {},
    }
    db.users.insert_one(doc)
    token = token_for(email)
    set_session(response, token)
    return {"token": token, "email": email, "name": doc["name"], "entitlement": entitlement_for(doc)}


@app.post("/api/auth/login")
def login(body: Login, response: Response):
    db = require_db()
    email = body.email.lower()
    u = db.users.find_one({"email": email})
    if not u or not u.get("password_hash") or not pwd.verify(body.password, u.get("password_hash", "")):
        raise HTTPException(401, "Invalid credentials")
    token = token_for(email)
    set_session(response, token)
    return {"token": token, "email": email, "name": u.get("name", ""), "entitlement": entitlement_for(u)}


@app.post("/api/auth/google")
def google_login(body: GoogleCredential, response: Response):
    if not GOOGLE_CLIENT_ID or not google_id_token:
        raise HTTPException(503, "Google sign-in is not configured")
    try:
        info = google_id_token.verify_oauth2_token(body.credential, google_requests.Request(), GOOGLE_CLIENT_ID)
    except Exception:
        raise HTTPException(401, "Invalid Google credential")
    if not info.get("email_verified"):
        raise HTTPException(401, "Google email is not verified")
    email = info["email"].lower()
    name = info.get("name", "")
    db = require_db()
    plan = "pro_lifetime" if is_brava(email) else "free"
    db.users.update_one(
        {"email": email},
        {"$set": {"name": name, "auth_method": "google", "google_sub": info.get("sub"), "brava_lifetime": is_brava(email)},
         "$setOnInsert": {"created_at": utcnow(), "plan": plan, "usage": {}}},
        upsert=True,
    )
    if is_brava(email):
        db.users.update_one({"email": email}, {"$set": {"plan": "pro_lifetime"}})
    u = db.users.find_one({"email": email})
    token = token_for(email)
    set_session(response, token)
    return {"token": token, "email": email, "name": name, "entitlement": entitlement_for(u)}


@app.post("/api/auth/logout")
def logout(response: Response):
    response.delete_cookie(SESSION_COOKIE, path="/")
    return {"ok": True}


@app.get("/api/me")
def me(user=Depends(current_user)):
    u = user_doc(user)
    ent = entitlement_for(u)
    count = int(u.get("usage", {}).get(month_key(), 0))
    return {
        "email": user,
        "name": u.get("name", ""),
        "auth_method": u.get("auth_method", "password"),
        "entitlement": ent,
        "usage": {"month": month_key(), "count": count, "limit": ent["ai_limit"]},
    }


@app.post("/api/ai/work-order")
def ai_work_order(req: AIRequest, user=Depends(current_user)):
    consume_ai(user)
    prompt = f"""{mode_context(req.mode)}\nRewrite the technician notes below into a concise, factual, CMMS-ready work-order narrative in {req.language}. Preserve when present: complaint/request, observed condition, safety/energy-control status, diagnostics and measurements, root cause, corrective action, parts/materials, verification/test run, downtime, follow-up, and technician. Omit missing facts rather than guessing. Clearly label any unresolved cause as unconfirmed.\nAsset: {req.asset}\nAdditional context: {req.context}\nTECHNICIAN NOTES:\n{req.text}"""
    return {"result": llm(prompt, req.personality), "mode": req.mode}


@app.post("/api/ai/troubleshoot")
def ai_troubleshoot(req: AIRequest, user=Depends(current_user)):
    consume_ai(user)
    prompt = f"""{mode_context(req.mode)}\nCreate a ranked troubleshooting plan in {req.language} from the facts below. Start with safe, fast, non-invasive checks. For each likely cause, state the evidence that would prove or eliminate it. Flag LOTO/qualified-person/OEM/service-information boundaries. Never suggest bypassing safeguards. Distinguish known facts from hypotheses.\nAsset: {req.asset}\nContext: {req.context}\nFACTS:\n{req.text}"""
    return {"result": llm(prompt, req.personality), "mode": req.mode}


@app.post("/api/ai/handoff")
def ai_handoff(req: AIRequest, user=Depends(current_user)):
    consume_ai(user)
    prompt = f"""{mode_context(req.mode)}\nTurn these notes into a concise shift/technician handoff in {req.language}: asset/vehicle, current state, request/symptom, checks completed, findings, changes, parts, state when left, temporary conditions/risks, remaining work, next recommended check, and people/vendor involved. Do not invent missing facts.\n{req.text}"""
    return {"result": llm(prompt, req.personality), "mode": req.mode}


@app.post("/api/work-orders")
def save_work_order(body: SaveWorkOrder, user=Depends(current_user)):
    db = require_db()
    doc = {
        "id": str(uuid.uuid4()),
        "owner": user,
        "mode": body.mode,
        "data": body.data.model_dump(),
        "narrative": body.narrative,
        "created_at": utcnow(),
    }
    db.work_orders.insert_one(doc)
    doc.pop("_id", None)
    doc["created_at"] = doc["created_at"].isoformat()
    return doc


@app.get("/api/work-orders")
def list_work_orders(user=Depends(current_user)):
    db = require_db()
    docs = []
    for d in db.work_orders.find({"owner": user}, {"_id": 0}).sort("created_at", -1).limit(100):
        if isinstance(d.get("created_at"), datetime):
            d["created_at"] = d["created_at"].isoformat()
        docs.append(d)
    return docs


@app.get("/api/knowledge/search")
def knowledge_search(q: str, user=Depends(current_user)):
    db = require_db()
    terms = [x for x in q.strip().split() if len(x) > 2][:6]
    if not terms:
        return []
    regex = "|".join(terms)
    docs = list(db.work_orders.find({"owner": user, "$or": [
        {"narrative": {"$regex": regex, "$options": "i"}},
        {"data.asset": {"$regex": regex, "$options": "i"}},
        {"data.complaint": {"$regex": regex, "$options": "i"}},
    ]}, {"_id": 0}).sort("created_at", -1).limit(20))
    for d in docs:
        if isinstance(d.get("created_at"), datetime):
            d["created_at"] = d["created_at"].isoformat()
    return docs


def stripe_key():
    return os.getenv("STRIPE_SECRET_KEY_LIVE") or os.getenv("STRIPE_SECRET_KEY") or ""


def stripe_price(plan: str):
    if plan == "starter":
        return os.getenv("STRIPE_PRICE_WRENCH_STARTER") or os.getenv("STRIPE_PRICE_STARTER")
    if plan == "pro":
        return os.getenv("STRIPE_PRICE_WRENCH_PRO") or os.getenv("STRIPE_PRICE_PRO") or os.getenv("STRIPE_PRICE_ID")
    return None


@app.post("/api/billing/checkout")
def billing_checkout(body: CheckoutRequest, request: Request, user=Depends(current_user)):
    if body.plan not in {"starter", "pro"}:
        raise HTTPException(400, "Unknown plan")
    u = user_doc(user)
    if is_brava(user):
        raise HTTPException(409, "Brava Tile accounts already have Pro Lifetime access")
    key = stripe_key()
    price = stripe_price(body.plan)
    if not stripe or not key or not price:
        raise HTTPException(503, "Billing is not configured")
    stripe.api_key = key
    session = stripe.checkout.Session.create(
        mode="subscription",
        line_items=[{"price": price, "quantity": 1}],
        customer_email=user if not u.get("stripe_customer_id") else None,
        customer=u.get("stripe_customer_id") or None,
        client_reference_id=user,
        metadata={"email": user, "plan": body.plan},
        success_url=f"{FRONTEND_URL}/?billing=success",
        cancel_url=f"{FRONTEND_URL}/?billing=cancel",
        allow_promotion_codes=True,
    )
    return {"url": session.url}


@app.post("/api/billing/portal")
def billing_portal(user=Depends(current_user)):
    u = user_doc(user)
    key = stripe_key()
    if not stripe or not key or not u.get("stripe_customer_id"):
        raise HTTPException(503, "Billing portal is not available")
    stripe.api_key = key
    s = stripe.billing_portal.Session.create(customer=u["stripe_customer_id"], return_url=f"{FRONTEND_URL}/")
    return {"url": s.url}


@app.post("/api/billing/webhook")
async def billing_webhook(request: Request):
    if not stripe or not stripe_key():
        raise HTTPException(503, "Billing is not configured")
    payload = await request.body()
    signature = request.headers.get("stripe-signature", "")
    secret = os.getenv("STRIPE_WEBHOOK_SECRET", "")
    if not secret:
        raise HTTPException(503, "Stripe webhook verification is not configured")
    stripe.api_key = stripe_key()
    try:
        event = stripe.Webhook.construct_event(payload, signature, secret)
    except Exception:
        raise HTTPException(400, "Invalid webhook")
    db = require_db()
    obj = event["data"]["object"]
    if event["type"] == "checkout.session.completed":
        email = (obj.get("metadata") or {}).get("email") or obj.get("client_reference_id")
        plan = (obj.get("metadata") or {}).get("plan", "pro")
        if email:
            db.users.update_one({"email": email.lower()}, {"$set": {"plan": plan, "stripe_customer_id": obj.get("customer"), "stripe_subscription_id": obj.get("subscription")}})
    elif event["type"] in {"customer.subscription.deleted", "customer.subscription.paused"}:
        sub_id = obj.get("id")
        u = db.users.find_one({"stripe_subscription_id": sub_id})
        if u and not is_brava(u.get("email", "")):
            db.users.update_one({"_id": u["_id"]}, {"$set": {"plan": "free"}})
    return {"received": True}


@app.get("/api/admin/status")
def admin_status(user=Depends(current_user)):
    admin_email = os.getenv("ADMIN_EMAIL", "").lower()
    if admin_email and user.lower() != admin_email:
        raise HTTPException(403, "Admin only")
    return {
        "database_configured": bool(MONGO_URL),
        "ai_configured": bool(OPENAI_API_KEY),
        "stripe_configured": bool(stripe_key()),
        "google_configured": bool(GOOGLE_CLIENT_ID),
        "frontend_url": FRONTEND_URL,
        "version": APP_VERSION,
    }
