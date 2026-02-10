from typing import Any, Literal

from pydantic import BaseModel, ConfigDict, Field, field_validator

DecisionLiteral = Literal["BUY", "SELL", "HOLD"]


class SuggestedVendor(BaseModel):
    name: str
    reason: str
    confidence: float = Field(ge=0.0, le=1.0)
    supporting_articles: list[int]


class MarketSignal(BaseModel):
    signal_type: Literal[
        "trend",
        "opportunity",
        "risk",
        "alert",
    ]
    label: str
    confidence: float = Field(ge=0.0, le=1.0)
    supporting_articles: list[int]
    suggested_vendors: list[SuggestedVendor] = Field(default_factory=list)


class InvestmentDebateStateModel(BaseModel):
    bull_history: str = ""
    bear_history: str = ""
    history: str = ""
    current_response: str = ""
    judge_decision: str = ""
    count: int = 0


class RiskDebateStateModel(BaseModel):
    aggressive_history: str = ""
    conservative_history: str = ""
    neutral_history: str = ""
    history: str = ""
    latest_speaker: str = ""
    current_aggressive_response: str = ""
    current_conservative_response: str = ""
    current_neutral_response: str = ""
    judge_decision: str = ""
    count: int = 0


class FinalStateModel(BaseModel):
    model_config = ConfigDict(extra="allow")

    company_of_interest: str
    trade_date: str
    sender: str | None = None

    messages: list[Any] = Field(default_factory=list)

    market_report: str = ""
    sentiment_report: str = ""
    news_report: str = ""
    fundamentals_report: str = ""

    investment_debate_state: InvestmentDebateStateModel = Field(
        default_factory=InvestmentDebateStateModel
    )
    investment_plan: str = ""
    trader_investment_plan: str = ""

    risk_debate_state: RiskDebateStateModel = Field(
        default_factory=RiskDebateStateModel
    )
    final_trade_decision: str = ""


class PropagateResultModel(BaseModel):
    final_state: FinalStateModel
    decision: DecisionLiteral

    @field_validator("decision", mode="before")
    @classmethod
    def normalize_decision(cls, value: Any) -> DecisionLiteral:
        text = str(value).strip().upper()
        if "BUY" in text:
            return "BUY"
        if "SELL" in text:
            return "SELL"
        return "HOLD"


class VendorRunResult(BaseModel):
    ticker: str
    analysis_date: str
    signal_type: Literal["trend", "opportunity", "risk", "alert"]
    signal_label: str
    vendor_reason: str
    vendor_confidence: float = Field(ge=0.0, le=1.0)
    decision: DecisionLiteral
    final_state: FinalStateModel


class StrategyBatchResult(BaseModel):
    provider: str
    quick_model: str
    deep_model: str
    analysis_date: str
    results: list[VendorRunResult] = Field(default_factory=list)
