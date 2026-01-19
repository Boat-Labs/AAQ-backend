from fastapi import APIRouter

from app.core.strategy.models import Strategy
from app.core.strategy.service import recommend_strategy, save_strategy

router = APIRouter()


@router.post("/recommend")
def recommend_strategy_endpoint(user_id: str):
    return recommend_strategy(user_id)


@router.post("/")
def create_strategy(strategy: Strategy):
    return {"message": "Strategy stored", "strategy": save_strategy(strategy)}
