from fastapi import APIRouter, HTTPException, Query
from pydantic import BaseModel

from app.core.strategy.models import MarketSignal, StrategyBatchResult
from app.core.strategy.service import (
    run_market_signal_strategy,
    run_mock_market_signal_strategy,
)

router = APIRouter()


class StrategyRunResponse(BaseModel):
    batch: StrategyBatchResult
    output_path: str | None = None


@router.post("/market-signal", response_model=StrategyBatchResult)
def run_strategy_from_market_signal(signal: MarketSignal):
    try:
        return run_market_signal_strategy(signal)
    except ValueError as exc:
        raise HTTPException(status_code=400, detail=str(exc)) from exc


@router.post("/market-signal/mock", response_model=StrategyRunResponse)
def run_strategy_from_mock_market_signal(
    persist_result: bool = Query(default=False),
    output_dir: str | None = Query(default=None),
):
    try:
        batch, save_path = run_mock_market_signal_strategy(
            persist_result=persist_result,
            output_dir=output_dir,
        )
        return StrategyRunResponse(
            batch=batch,
            output_path=str(save_path) if save_path else None,
        )
    except ValueError as exc:
        raise HTTPException(status_code=400, detail=str(exc)) from exc
