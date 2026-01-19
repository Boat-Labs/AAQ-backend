from fastapi import APIRouter

from app.core.activities.router import router as activities_router
from app.core.goal.router import router as goal_router
from app.core.market_intelligence.router import router as market_router
from app.core.performance.router import router as performance_router
from app.core.strategy.router import router as strategy_router
from app.core.user.router import router as user_router

api_router = APIRouter(prefix="/api")

api_router.include_router(user_router, prefix="/users", tags=["Users"])
api_router.include_router(goal_router, prefix="/goals", tags=["Goals"])
api_router.include_router(market_router, prefix="/market", tags=["Market Intelligence"])
api_router.include_router(strategy_router, prefix="/strategies", tags=["Strategies"])
api_router.include_router(activities_router, prefix="/activities", tags=["User Activities"])
api_router.include_router(performance_router, prefix="/performance", tags=["Performance"])
