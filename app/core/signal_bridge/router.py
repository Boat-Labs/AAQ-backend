from fastapi import APIRouter, Query

from app.core.signal_bridge.models import SignalGenerationRequest
from app.core.signal_bridge.service import FOCUS_AREA_MAPPINGS, generate_market_signal
from app.core.strategy.service import run_market_signal_strategy

router = APIRouter()


@router.get("/mappings")
def get_mappings():
    return FOCUS_AREA_MAPPINGS


@router.post("/generate")
def generate_signal(request: SignalGenerationRequest):
    return generate_market_signal(request)


@router.post("/pipeline")
def run_pipeline(
    request: SignalGenerationRequest,
    dry_run: bool = Query(default=False),
):
    signal = generate_market_signal(request)

    if dry_run:
        return {"signal": signal}

    batch_result = run_market_signal_strategy(signal)
    return {"signal": signal, "strategy_result": batch_result}
