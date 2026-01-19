from pydantic import BaseModel


class PortfolioPerformance(BaseModel):
    total_return: float
    benchmark_return: float
    alpha: float
    period: str
