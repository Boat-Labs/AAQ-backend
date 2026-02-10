import os
from datetime import datetime
from pathlib import Path

from app.core.strategy.models import MarketSignal
from app.core.strategy.trading_strategy import TradingStrategy, save_batch_result
from dotenv import load_dotenv


def build_mock_market_signal() -> MarketSignal:
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


def run_real_pipeline_with_mock_signal() -> Path:
    """
    Integration-style execution:
    - uses mock MarketSignal payload
    - runs the real TradingStrategy / TradingAgentsGraph pipeline
    - writes result JSON to disk
    """
    signal = build_mock_market_signal()
    strategy = TradingStrategy()
    batch = strategy.run_market_signal(signal)

    output_dir = Path(
        os.getenv(
            "TA_INTEGRATION_OUTPUT_DIR",
            f"./results/integration/{datetime.now().strftime('%Y%m%d_%H%M%S')}",
        )
    )
    output_file = output_dir / "mock_market_signal_pipeline_result.json"
    save_path = save_batch_result(batch, output_file)
    return save_path


def main():
    load_dotenv()

    try:
        save_path = run_real_pipeline_with_mock_signal()
        print(f"Integration pipeline completed successfully. Output: {save_path}")
    except Exception as exc:
        print("Integration pipeline failed.")
        print(f"Error: {exc}")
        raise SystemExit(1)


if __name__ == "__main__":
    main()
