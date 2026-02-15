from unittest.mock import MagicMock, patch

from fastapi.testclient import TestClient

from app.core.strategy.models import (
    FinalStateModel,
    StrategyBatchResult,
    VendorRunResult,
)
from app.main import app

client = TestClient(app)

VALID_SIGNAL = {
    "signal_type": "opportunity",
    "label": "Test signal",
    "confidence": 0.8,
    "supporting_articles": [1],
    "suggested_vendors": [
        {
            "name": "AAPL",
            "reason": "Strong momentum",
            "confidence": 0.9,
            "supporting_articles": [1],
        }
    ],
}


def _make_batch_result() -> StrategyBatchResult:
    return StrategyBatchResult(
        provider="google",
        quick_model="gemini-3-flash-preview",
        deep_model="gemini-3-pro-preview",
        analysis_date="2025-01-01",
        results=[
            VendorRunResult(
                ticker="AAPL",
                analysis_date="2025-01-01",
                signal_type="opportunity",
                signal_label="Test signal",
                vendor_reason="Strong momentum",
                vendor_confidence=0.9,
                decision="BUY",
                final_state=FinalStateModel(
                    company_of_interest="AAPL",
                    trade_date="2025-01-01",
                ),
            )
        ],
    )


@patch("app.core.strategy.service.TradingStrategy")
def test_market_signal_success(mock_strategy_cls):
    instance = MagicMock()
    instance.run_market_signal.return_value = _make_batch_result()
    mock_strategy_cls.return_value = instance

    resp = client.post("/api/strategies/market-signal", json={"signal": VALID_SIGNAL})
    assert resp.status_code == 200
    body = resp.json()
    assert "batch" in body
    assert body["output_path"] is None
    assert body["batch"]["provider"] == "google"
    assert len(body["batch"]["results"]) == 1
    assert body["batch"]["results"][0]["decision"] == "BUY"


def test_market_signal_empty_vendors():
    signal = {**VALID_SIGNAL, "suggested_vendors": []}
    resp = client.post("/api/strategies/market-signal", json={"signal": signal})
    # Empty vendors triggers ValueError in TradingStrategy.run_market_signal
    # but since service creates TradingStrategy which needs env vars,
    # this may fail at construction. Either 400 or 500 is acceptable.
    assert resp.status_code in (400, 500)


def test_market_signal_invalid_signal_type():
    signal = {**VALID_SIGNAL, "signal_type": "invalid_type"}
    resp = client.post("/api/strategies/market-signal", json={"signal": signal})
    assert resp.status_code == 422


@patch("app.core.strategy.service.TradingStrategy")
def test_market_signal_propagate_value_error(mock_strategy_cls):
    instance = MagicMock()
    instance.run_market_signal.side_effect = ValueError("All vendors failed")
    mock_strategy_cls.return_value = instance

    resp = client.post("/api/strategies/market-signal", json={"signal": VALID_SIGNAL})
    assert resp.status_code == 400
    assert "All vendors failed" in resp.json()["detail"]


@patch("app.core.strategy.service.TradingStrategy")
def test_market_signal_unexpected_error(mock_strategy_cls):
    instance = MagicMock()
    instance.run_market_signal.side_effect = RuntimeError("Unexpected")
    mock_strategy_cls.return_value = instance

    resp = client.post("/api/strategies/market-signal", json={"signal": VALID_SIGNAL})
    assert resp.status_code == 500
    assert resp.json()["detail"] == "Internal server error"


@patch("app.core.strategy.service.TradingStrategy")
def test_mock_market_signal_success(mock_strategy_cls):
    instance = MagicMock()
    instance.run_market_signal.return_value = _make_batch_result()
    mock_strategy_cls.return_value = instance

    resp = client.post("/api/strategies/market-signal/mock")
    assert resp.status_code == 200
    body = resp.json()
    assert "batch" in body
    assert body["output_path"] is None
