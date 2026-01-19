from fastapi import APIRouter

from app.core.market_intelligence.models import MarketSnapshot
from app.core.market_intelligence.service import ingest_snapshot

router = APIRouter()


@router.post("/snapshot")
def create_snapshot(snapshot: MarketSnapshot):
    return {"message": "Snapshot received", "snapshot": ingest_snapshot(snapshot)}
