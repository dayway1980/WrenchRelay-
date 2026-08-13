"""Contextual vendor ad slots for maintenance work, ready for vendor inventory."""

from fastapi import APIRouter

from security import CurrentUser, require_organization


router = APIRouter(prefix="/organizations/{organization_id}/ads", tags=["vendor ads"])

VENDOR_ADS = [
    {"vendor": "Grainger", "category": "Parts supplier", "keywords": ["bearing", "belt", "pump", "conveyor"], "headline": "Keep critical spares within reach", "cta": "Browse maintenance parts"},
    {"vendor": "Fastenal", "category": "Parts supplier", "keywords": ["fastener", "bolt", "hardware", "bearing"], "headline": "Stock the hardware that keeps lines moving", "cta": "Find shop supplies"},
    {"vendor": "MSC", "category": "Tooling & MRO", "keywords": ["tool", "motor", "lubricant", "bearing"], "headline": "MRO supplies for your next shutdown", "cta": "See MRO catalog"},
    {"vendor": "Lubrication partner", "category": "Lubricant supplier", "keywords": ["oil", "grease", "lubricant", "gearbox"], "headline": "Protect equipment between planned maintenance", "cta": "Explore lubricant programs"},
]


@router.get("")
async def relevant_ads(organization_id: str, user: CurrentUser, query: str = ""):
    await require_organization(user, organization_id, "work_orders:read")
    text = query.lower()
    matches = [ad for ad in VENDOR_ADS if any(keyword in text for keyword in ad["keywords"])]
    ads = matches[:2] or [{"vendor": "Advertise here", "category": "Vendor partnership", "headline": "Reach maintenance technicians where work happens", "cta": "Advertise to 10,000+ maintenance technicians"}]
    return {"sidebar": ads[0], "banner": ads[-1]}
