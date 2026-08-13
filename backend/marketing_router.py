"""Marketing router — serves ad / vendor partnership endpoints.

Currently a placeholder that returns empty ad placements.
Will be connected to a real ad-serving backend once vendor
partnerships are finalized.
"""

from fastapi import APIRouter

router = APIRouter(prefix="/api/marketing", tags=["marketing"])


@router.get("/ads")
async def get_ads(slot: str = "default"):
    """Return ads for a given slot.

    Currently returns an empty list (no active campaigns).
    """
    return {"slot": slot, "ads": []}


@router.get("/health")
async def marketing_health():
    return {"status": "ok", "module": "marketing"}


# Future: POST /api/marketing/impressions
# Future: POST /api/marketing/clicks
# Future: GET /api/marketing/campaigns (admin)
# Future: analytics aggregation endpoint
