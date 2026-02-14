from __future__ import annotations

import json
import logging
import os
import sys
from concurrent.futures import ThreadPoolExecutor, as_completed
from dataclasses import dataclass
from datetime import datetime
from pathlib import Path
from typing import Callable, Protocol

from app.core.strategy.models import (
    FinalStateModel,
    MarketSignal,
    PropagateResultModel,
    StrategyBatchResult,
    VendorRunResult,
)

try:
    from app.core.tradingagents.default_config import DEFAULT_CONFIG
except ModuleNotFoundError:
    core_dir = str(Path(__file__).resolve().parents[1])
    if core_dir not in sys.path:
        sys.path.insert(0, core_dir)
    from tradingagents.default_config import DEFAULT_CONFIG

logger = logging.getLogger(__name__)


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
    research_depth: int
    debug: bool
    analysis_date: str
    analysts: list[str]
    max_parallel_tickers: int

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
        research_depth = int(os.getenv("TA_RESEARCH_DEPTH", "1"))
        max_parallel_tickers = int(os.getenv("TA_MAX_PARALLEL_TICKERS", "1"))
        debug = parse_env_bool("TA_DEBUG", False)
        analysis_date = resolve_analysis_date()
        analysts = resolve_selected_analysts_from_env()

        if research_depth < 1:
            raise ValueError("TA_RESEARCH_DEPTH must be >= 1")
        if max_parallel_tickers < 1:
            raise ValueError("TA_MAX_PARALLEL_TICKERS must be >= 1")
        if provider != "google":
            raise ValueError(
                "This strategy script is configured for Gemini workflow. Set TA_LLM_PROVIDER=google."
            )
        if google_thinking_level is not None and google_thinking_level not in {"high", "minimal"}:
            raise ValueError("TA_GOOGLE_THINKING_LEVEL must be one of: high, minimal")

        return cls(
            provider=provider,
            backend_url=backend_url,
            quick_model=quick_model,
            deep_model=deep_model,
            google_thinking_level=google_thinking_level,
            research_depth=research_depth,
            max_parallel_tickers=max_parallel_tickers,
            debug=debug,
            analysis_date=analysis_date,
            analysts=analysts,
        )


def build_runtime_config(settings: StrategySettings) -> dict:
    config = DEFAULT_CONFIG.copy()
    config["llm_provider"] = settings.provider
    config["backend_url"] = settings.backend_url
    config["quick_think_llm"] = settings.quick_model
    config["deep_think_llm"] = settings.deep_model
    config["google_thinking_level"] = settings.google_thinking_level
    config["max_debate_rounds"] = settings.research_depth
    config["max_risk_discuss_rounds"] = settings.research_depth
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

    @staticmethod
    def _is_google_thought_signature_error(exc: Exception) -> bool:
        message = str(exc).lower()
        return "thought_signature" in message and "gemini" in message

    def _process_single_vendor(
        self, vendor, signal: MarketSignal, index: int, total: int,
    ) -> VendorRunResult | None:
        """Process a single vendor ticker. Returns None on failure."""
        ticker = vendor.name
        logger.info("Processing vendor %d/%d: %s", index, total, ticker)

        # Each vendor gets its own graph instance for thread-safety
        graph = self.graph_factory(
            self.settings.analysts, self.settings.debug, self.config,
        )

        try:
            final_state_raw, decision_raw = graph.propagate(
                ticker, self.settings.analysis_date
            )
        except Exception as exc:
            if (
                self.settings.provider == "google"
                and self._is_google_thought_signature_error(exc)
            ):
                logger.warning(
                    "Google thought_signature error for %s, retrying without thinking",
                    ticker,
                )
                fallback_config = self.config.copy()
                fallback_config["google_thinking_level"] = None
                fallback_graph = self.graph_factory(
                    self.settings.analysts, self.settings.debug, fallback_config,
                )
                try:
                    final_state_raw, decision_raw = fallback_graph.propagate(
                        ticker, self.settings.analysis_date
                    )
                except Exception:
                    logger.exception(
                        "Vendor %s failed on fallback retry, skipping", ticker,
                    )
                    return None
            else:
                logger.exception(
                    "Vendor %s failed during propagate, skipping", ticker,
                )
                return None

        try:
            propagate_result = PropagateResultModel(
                final_state=FinalStateModel.model_validate(final_state_raw),
                decision=decision_raw,
            )
        except Exception:
            logger.exception(
                "Vendor %s result validation failed, skipping", ticker,
            )
            return None

        logger.info(
            "Vendor %s completed: decision=%s", ticker, propagate_result.decision,
        )
        return VendorRunResult(
            ticker=ticker,
            analysis_date=self.settings.analysis_date,
            signal_type=signal.signal_type,
            signal_label=signal.label,
            vendor_reason=vendor.reason,
            vendor_confidence=vendor.confidence,
            decision=propagate_result.decision,
            final_state=propagate_result.final_state,
        )

    def run_market_signal(self, signal: MarketSignal) -> StrategyBatchResult:
        if not signal.suggested_vendors:
            raise ValueError("MarketSignal.suggested_vendors cannot be empty")

        total = len(signal.suggested_vendors)
        max_workers = min(self.settings.max_parallel_tickers, total)

        if max_workers == 1:
            # Sequential path (preserves original behavior)
            results = []
            for i, vendor in enumerate(signal.suggested_vendors, 1):
                result = self._process_single_vendor(vendor, signal, i, total)
                if result is not None:
                    results.append(result)
        else:
            # Parallel path
            results = []
            with ThreadPoolExecutor(max_workers=max_workers) as executor:
                futures = {
                    executor.submit(
                        self._process_single_vendor, vendor, signal, i, total,
                    ): vendor.name
                    for i, vendor in enumerate(signal.suggested_vendors, 1)
                }
                for future in as_completed(futures):
                    ticker = futures[future]
                    try:
                        result = future.result()
                        if result is not None:
                            results.append(result)
                    except Exception:
                        logger.exception(
                            "Vendor %s raised unexpected error", ticker,
                        )

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
    from dotenv import load_dotenv
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
