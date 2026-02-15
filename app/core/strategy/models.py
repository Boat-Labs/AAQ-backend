from typing import Any, Literal

from pydantic import BaseModel, ConfigDict, Field, field_validator

DecisionLiteral = Literal["BUY", "SELL", "HOLD"]


def _coerce_gemini_content(value: Any) -> str:
    """Coerce Gemini thinking-mode content blocks to plain text.

    Gemini 3 with thinking enabled returns list[dict] like:
    [{"type": "text", "text": "...", "thought_signature": "..."}]
    instead of a plain string.
    """
    if isinstance(value, str):
        return value
    if isinstance(value, list):
        parts = []
        for item in value:
            if isinstance(item, dict) and "text" in item:
                parts.append(item["text"])
            elif isinstance(item, str):
                parts.append(item)
        return "\n".join(parts)
    return str(value)


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

    @field_validator("*", mode="before")
    @classmethod
    def coerce_str_fields(cls, value: Any, info: Any) -> Any:
        if info.field_name == "count":
            return value
        return _coerce_gemini_content(value)


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

    @field_validator("*", mode="before")
    @classmethod
    def coerce_str_fields(cls, value: Any, info: Any) -> Any:
        if info.field_name == "count":
            return value
        return _coerce_gemini_content(value)


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

    _STR_FIELDS = {
        "market_report", "sentiment_report", "news_report",
        "fundamentals_report", "investment_plan",
        "trader_investment_plan", "final_trade_decision",
    }

    @field_validator(*_STR_FIELDS, mode="before")
    @classmethod
    def coerce_str_fields(cls, value: Any) -> str:
        return _coerce_gemini_content(value)


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
    quick_provider: str | None = None
    deep_provider: str | None = None
    quick_model: str
    deep_model: str
    analysis_date: str
    results: list[VendorRunResult] = Field(default_factory=list)
