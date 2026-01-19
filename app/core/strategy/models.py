from typing import List

from pydantic import BaseModel


class BacktestResult(BaseModel):
    sharpe_ratio: float
    max_drawdown: float
    win_rate: float


class Strategy(BaseModel):
    strategy_id: str
    strategy_type: str
    hypothesis: str
    indicators: List[str]
    backtest: BacktestResult
    risk_level: str
