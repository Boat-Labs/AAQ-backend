from fastapi import APIRouter

from app.core.performance.models import PortfolioPerformance
from app.core.performance.service import get_portfolio_performance, save_performance

router = APIRouter()


@router.get("/{user_id}")
def get_performance(user_id: str):
    return get_portfolio_performance(user_id)


@router.post("/")
def create_performance(performance: PortfolioPerformance):
    return {"message": "Performance stored", "performance": save_performance(performance)}
