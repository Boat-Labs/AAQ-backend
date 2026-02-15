from __future__ import annotations

import json
import logging
import os
import sys
from dataclasses import dataclass
from datetime import datetime
from pathlib import Path
from typing import Callable, Protocol

from dotenv import load_dotenv

logger = logging.getLogger(__name__)

load_dotenv()

from app.core.strategy.models import (  # noqa: E402
    FinalStateModel,
    MarketSignal,
    PropagateResultModel,
    StrategyBatchResult,
    VendorRunResult,
)
from app.core.strategy.schemas import ModelSelectionRequest  # noqa: E402

try:
    from app.core.tradingagents.default_config import DEFAULT_CONFIG
except ModuleNotFoundError:
    core_dir = str(Path(__file__).resolve().parents[1])
    if core_dir not in sys.path:
        sys.path.insert(0, core_dir)
    from tradingagents.default_config import DEFAULT_CONFIG


class TradingGraphLike(Protocol):
    def propagate(self, company_name: str, trade_date: str):
        ...


GraphFactory = Callable[[list[str], bool, dict], TradingGraphLike]


def parse_env_bool(name: str, default: bool) -> bool:
    value = os.getenv(name)
    if value is None:
        return default
    normalized = value.strip().lower()
    if normalized in {"1", "true", "yes", "y", "on"}:
        return True
    if normalized in {"0", "false", "no", "n", "off"}:
        return False
    raise ValueError(f"Invalid boolean for {name}: {value}")


def resolve_analysis_date() -> str:
    value = os.getenv("TA_ANALYSIS_DATE")
    if value and value.strip():
        parsed = datetime.strptime(value.strip(), "%Y-%m-%d")
        if parsed.date() > datetime.now().date():
            raise ValueError("TA_ANALYSIS_DATE cannot be in the future")
        return value.strip()
    return datetime.now().strftime("%Y-%m-%d")


def resolve_selected_analysts_from_env() -> list[str]:
    analysts = []
    if parse_env_bool("TA_ANALYST_MARKET", True):
        analysts.append("market")
    if parse_env_bool("TA_ANALYST_SOCIAL", True):
        analysts.append("social")
    if parse_env_bool("TA_ANALYST_NEWS", True):
        analysts.append("news")
    if parse_env_bool("TA_ANALYST_FUNDAMENTALS", True):
        analysts.append("fundamentals")

    if not analysts:
        raise ValueError("At least one analyst must be enabled with TA_ANALYST_*")
    return analysts


@dataclass
class StrategySettings:
    provider: str
    backend_url: str
    quick_model: str
    deep_model: str
    google_thinking_level: str | None
    openai_reasoning_effort: str | None
    research_depth: int
    debug: bool
    analysis_date: str
    analysts: list[str]
    quick_provider: str | None = None
    quick_backend_url: str | None = None
    deep_provider: str | None = None
    deep_backend_url: str | None = None

    @classmethod
    def from_env(cls) -> "StrategySettings":
        provider = os.getenv("TA_LLM_PROVIDER", "google").strip().lower()
        backend_url = os.getenv(
            "TA_BACKEND_URL", "https://generativelanguage.googleapis.com/v1"
        ).strip()
        quick_model = os.getenv("TA_QUICK_MODEL", "gemini-3-flash-preview").strip()
        deep_model = os.getenv("TA_DEEP_MODEL", "gemini-3-pro-preview").strip()
        google_thinking_level_raw = os.getenv("TA_GOOGLE_THINKING_LEVEL")
        google_thinking_level = (
            google_thinking_level_raw.strip().lower()
            if google_thinking_level_raw and google_thinking_level_raw.strip()
            else None
        )
        openai_reasoning_effort_raw = os.getenv("TA_OPENAI_REASONING_EFFORT")
        openai_reasoning_effort = (
            openai_reasoning_effort_raw.strip().lower()
            if openai_reasoning_effort_raw and openai_reasoning_effort_raw.strip()
            else None
        )
        research_depth = int(os.getenv("TA_RESEARCH_DEPTH", "1"))
        debug = parse_env_bool("TA_DEBUG", False)
        analysis_date = resolve_analysis_date()
        analysts = resolve_selected_analysts_from_env()

        if research_depth < 1:
            raise ValueError("TA_RESEARCH_DEPTH must be >= 1")
        if google_thinking_level is not None and google_thinking_level not in {"high", "minimal"}:
            raise ValueError("TA_GOOGLE_THINKING_LEVEL must be one of: high, minimal")

        return cls(
            provider=provider,
            backend_url=backend_url,
            quick_model=quick_model,
            deep_model=deep_model,
            google_thinking_level=google_thinking_level,
            openai_reasoning_effort=openai_reasoning_effort,
            research_depth=research_depth,
            debug=debug,
            analysis_date=analysis_date,
            analysts=analysts,
        )

    @classmethod
    def from_request(
        cls,
        req: ModelSelectionRequest,
    ) -> StrategySettings:
        """Create settings from env defaults, overriding with request params."""
        base = cls.from_env()
        if req.quick_provider:
            base.quick_provider = req.quick_provider
        if req.quick_model:
            base.quick_model = req.quick_model
        if req.quick_backend_url:
            base.quick_backend_url = req.quick_backend_url
        if req.deep_provider:
            base.deep_provider = req.deep_provider
        if req.deep_model:
            base.deep_model = req.deep_model
        if req.deep_backend_url:
            base.deep_backend_url = req.deep_backend_url
        if req.google_thinking_level:
            base.google_thinking_level = req.google_thinking_level
        if req.openai_reasoning_effort:
            base.openai_reasoning_effort = req.openai_reasoning_effort
        return base


def build_runtime_config(settings: StrategySettings) -> dict:
    config = DEFAULT_CONFIG.copy()
    config["llm_provider"] = settings.provider
    config["backend_url"] = settings.backend_url
    config["quick_think_llm"] = settings.quick_model
    config["deep_think_llm"] = settings.deep_model
    config["google_thinking_level"] = settings.google_thinking_level
    config["openai_reasoning_effort"] = settings.openai_reasoning_effort
    config["max_debate_rounds"] = settings.research_depth
    config["max_risk_discuss_rounds"] = settings.research_depth
    # Per-role provider overrides
    config["quick_think_provider"] = settings.quick_provider
    config["quick_think_backend_url"] = settings.quick_backend_url
    config["deep_think_provider"] = settings.deep_provider
    config["deep_think_backend_url"] = settings.deep_backend_url
    return config


def default_graph_factory(
    selected_analysts: list[str], debug: bool, config: dict
) -> TradingGraphLike:
    try:
        from app.core.tradingagents.graph.trading_graph import TradingAgentsGraph
    except ModuleNotFoundError:
        core_dir = str(Path(__file__).resolve().parents[1])
        if core_dir not in sys.path:
            sys.path.insert(0, core_dir)
        from tradingagents.graph.trading_graph import TradingAgentsGraph

    return TradingAgentsGraph(
        selected_analysts=selected_analysts,
        debug=debug,
        config=config,
    )


class TradingStrategy:
    def __init__(
        self,
        settings: StrategySettings | None = None,
        graph_factory: GraphFactory | None = None,
    ):
        self.settings = settings or StrategySettings.from_env()
        self.graph_factory = graph_factory or default_graph_factory
        self.config = build_runtime_config(self.settings)
        self.graph = self.graph_factory(
            self.settings.analysts,
            self.settings.debug,
            self.config,
        )

    @staticmethod
    def _is_google_thought_signature_error(exc: Exception) -> bool:
        message = str(exc).lower()
        return "thought_signature" in message and "gemini" in message

    def run_market_signal(self, signal: MarketSignal) -> StrategyBatchResult:
        if not signal.suggested_vendors:
            raise ValueError("MarketSignal.suggested_vendors cannot be empty")

        results: list[VendorRunResult] = []

        for i, vendor in enumerate(signal.suggested_vendors, 1):
            ticker = vendor.name
            logger.info(
                "Processing vendor %d/%d: %s",
                i, len(signal.suggested_vendors), ticker,
            )

            try:
                final_state_raw, decision_raw = self.graph.propagate(
                    ticker, self.settings.analysis_date
                )
            except Exception as exc:
                uses_google = (
                    self.settings.provider == "google"
                    or self.settings.quick_provider == "google"
                    or self.settings.deep_provider == "google"
                )
                if (
                    uses_google
                    and self._is_google_thought_signature_error(exc)
                ):
                    # Automatic one-time fallback: disable Google thinking
                    # and retry the same ticker in the real pipeline.
                    logger.warning(
                        "Google thought_signature error for %s, retrying without thinking",
                        ticker,
                    )
                    fallback_config = self.config.copy()
                    fallback_config["google_thinking_level"] = None
                    self.config = fallback_config
                    self.graph = self.graph_factory(
                        self.settings.analysts,
                        self.settings.debug,
                        self.config,
                    )
                    try:
                        final_state_raw, decision_raw = self.graph.propagate(
                            ticker, self.settings.analysis_date
                        )
                    except Exception:
                        logger.exception(
                            "Vendor %s failed on fallback retry, skipping", ticker,
                        )
                        continue
                else:
                    logger.exception(
                        "Vendor %s failed during propagate, skipping", ticker,
                    )
                    continue

            try:
                propagate_result = PropagateResultModel(
                    final_state=FinalStateModel.model_validate(final_state_raw),
                    decision=decision_raw,
                )
            except Exception:
                logger.exception(
                    "Vendor %s result validation failed, skipping", ticker,
                )
                continue

            results.append(
                VendorRunResult(
                    ticker=ticker,
                    analysis_date=self.settings.analysis_date,
                    signal_type=signal.signal_type,
                    signal_label=signal.label,
                    vendor_reason=vendor.reason,
                    vendor_confidence=vendor.confidence,
                    decision=propagate_result.decision,
                    final_state=propagate_result.final_state,
                )
            )
            logger.info("Vendor %s completed: decision=%s", ticker, propagate_result.decision)

        if not results:
            raise ValueError(
                "All vendors failed during analysis. Check server logs for details."
            )

        return StrategyBatchResult(
            provider=self.settings.provider,
            quick_model=self.settings.quick_model,
            deep_model=self.settings.deep_model,
            analysis_date=self.settings.analysis_date,
            results=results,
        )


def load_market_signal_from_json(path: str | Path) -> MarketSignal:
    payload = json.loads(Path(path).read_text(encoding="utf-8"))
    return MarketSignal.model_validate(payload)


def default_mock_market_signal() -> MarketSignal:
    return MarketSignal.model_validate(
        {
            "signal_type": "opportunity",
            "label": "Consumer electronics momentum with AI smartphone catalysts",
            "confidence": 0.78,
            "supporting_articles": [1, 2, 6],
            "suggested_vendors": [
                {
                    "name": "Xiaomi",
                    "reason": "Strong handset ecosystem growth and AI feature rollout expectations",
                    "confidence": 0.86,
                    "supporting_articles": [1, 2, 6],
                }
            ],
        }
    )


def save_batch_result(batch: StrategyBatchResult, output_path: str | Path) -> Path:
    path = Path(output_path)
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(batch.model_dump_json(indent=2), encoding="utf-8")
    return path


def main():
    load_dotenv()

    signal_path = os.getenv("SIGNAL_JSON_PATH")
    signal = (
        load_market_signal_from_json(signal_path)
        if signal_path
        else default_mock_market_signal()
    )

    strategy = TradingStrategy()
    batch = strategy.run_market_signal(signal)

    print(batch.model_dump_json(indent=2))


if __name__ == "__main__":
    main()
