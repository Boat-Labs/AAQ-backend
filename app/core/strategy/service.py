import os
from datetime import datetime
from pathlib import Path

from app.core.strategy.models import MarketSignal, StrategyBatchResult
from app.core.strategy.trading_strategy import (
    TradingStrategy,
    default_mock_market_signal,
    save_batch_result,
)


def run_market_signal_strategy(signal: MarketSignal) -> StrategyBatchResult:
    strategy = TradingStrategy()
    return strategy.run_market_signal(signal)


def run_mock_market_signal_strategy(
    persist_result: bool = False,
    output_dir: str | None = None,
) -> tuple[StrategyBatchResult, Path | None]:
    batch = run_market_signal_strategy(default_mock_market_signal())

    if not persist_result:
        return batch, None

    target_dir = Path(
        output_dir
        or os.getenv(
            "TA_INTEGRATION_OUTPUT_DIR",
            f"./results/integration/{datetime.now().strftime('%Y%m%d_%H%M%S')}",
        )
    )
    output_file = target_dir / "mock_market_signal_pipeline_result.json"
    save_path = save_batch_result(batch, output_file)
    return batch, save_path
