from app.core.performance.models import PortfolioPerformance


def get_portfolio_performance(user_id: str):
    return {"user_id": user_id, "performance": "calculated"}


def save_performance(performance: PortfolioPerformance):
    return performance
