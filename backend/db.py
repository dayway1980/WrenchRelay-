"""Shared database helpers for WrenchRelay AI."""

import os
from datetime import datetime, timezone

from motor.motor_asyncio import AsyncIOMotorClient


client = AsyncIOMotorClient(os.environ["MONGO_URL"])
db = client[os.environ["DB_NAME"]]


def now_iso() -> str:
    return datetime.now(timezone.utc).isoformat()


async def create_indexes() -> None:
    await db.users.create_index("email", unique=True)
    await db.memberships.create_index([("organization_id", 1), ("user_id", 1)], unique=True)
    await db.assets.create_index([("organization_id", 1), ("asset_number", 1)])
    await db.work_orders.create_index([("organization_id", 1), ("work_order_number", 1)])
    await db.work_orders.create_index([("organization_id", 1), ("status", 1)])
    await db.invites.create_index("token", unique=True)
    await db.password_reset_tokens.create_index("expires_at", expireAfterSeconds=0)
    await db.login_attempts.create_index("identifier", unique=True)
