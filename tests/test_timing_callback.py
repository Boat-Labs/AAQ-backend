"""Tests for TimingCallbackHandler."""

import threading
import time
from unittest.mock import MagicMock
from uuid import uuid4

from langchain_core.outputs import ChatGeneration, LLMResult

from app.core.tradingagents.graph.timing_callback import (
    TimingCallbackHandler,
)


def _uid():
    return uuid4()


def _serialized(model="test-model"):
    return {"kwargs": {"model": model}, "id": ["langchain", "chat_models", "ChatOpenAI"]}


def _chain_serialized(name="Market Analyst"):
    return {"name": name, "id": ["langgraph", "graph", "StateGraph"]}


def _tool_serialized(name="get_stock_data"):
    return {"name": name}


def _llm_result_openai(prompt_tokens=100, completion_tokens=50, total_tokens=150):
    return LLMResult(
        generations=[[]],
        llm_output={
            "token_usage": {
                "prompt_tokens": prompt_tokens,
                "completion_tokens": completion_tokens,
                "total_tokens": total_tokens,
            }
        },
    )


def _llm_result_usage_metadata(input_tokens=200, output_tokens=80, total_tokens=280):
    msg = MagicMock()
    msg.usage_metadata = {
        "input_tokens": input_tokens,
        "output_tokens": output_tokens,
        "total_tokens": total_tokens,
    }
    gen = MagicMock(spec=ChatGeneration)
    gen.message = msg
    return LLMResult(generations=[[gen]], llm_output=None)


def _llm_result_no_tokens():
    return LLMResult(generations=[[]], llm_output=None)


class TestLLMCallbacks:
    def test_chat_model_start_end_records_timing(self):
        handler = TimingCallbackHandler()
        rid = _uid()

        handler.on_chat_model_start(
            _serialized("gemini-3-flash"), messages=[[]], run_id=rid
        )
        time.sleep(0.01)
        handler.on_llm_end(_llm_result_openai(), run_id=rid)

        assert len(handler.llm_calls) == 1
        record = handler.llm_calls[0]
        assert record.model == "gemini-3-flash"
        assert record.duration_s >= 0.01
        assert record.input_tokens == 100
        assert record.output_tokens == 50
        assert record.total_tokens == 150
        assert record.error is None

    def test_llm_start_end_records_timing(self):
        handler = TimingCallbackHandler()
        rid = _uid()

        handler.on_llm_start(_serialized("gpt-4"), prompts=["hello"], run_id=rid)
        time.sleep(0.01)
        handler.on_llm_end(_llm_result_openai(10, 20, 30), run_id=rid)

        assert len(handler.llm_calls) == 1
        record = handler.llm_calls[0]
        assert record.model == "gpt-4"
        assert record.duration_s >= 0.01
        assert record.total_tokens == 30

    def test_llm_error_records_error(self):
        handler = TimingCallbackHandler()
        rid = _uid()

        handler.on_llm_start(_serialized(), prompts=["hi"], run_id=rid)
        handler.on_llm_error(ValueError("rate limit"), run_id=rid)

        assert len(handler.llm_calls) == 1
        record = handler.llm_calls[0]
        assert record.error == "rate limit"
        assert record.duration_s >= 0


class TestTokenExtraction:
    def test_openai_style(self):
        handler = TimingCallbackHandler()
        result = handler._extract_token_usage(
            _llm_result_openai(500, 200, 700)
        )
        assert result == {
            "input_tokens": 500,
            "output_tokens": 200,
            "total_tokens": 700,
        }

    def test_usage_metadata_style(self):
        handler = TimingCallbackHandler()
        result = handler._extract_token_usage(
            _llm_result_usage_metadata(300, 100, 400)
        )
        assert result == {
            "input_tokens": 300,
            "output_tokens": 100,
            "total_tokens": 400,
        }

    def test_no_tokens_returns_zeros(self):
        handler = TimingCallbackHandler()
        result = handler._extract_token_usage(_llm_result_no_tokens())
        assert result == {"input_tokens": 0, "output_tokens": 0, "total_tokens": 0}


class TestChainCallbacks:
    def test_chain_start_end_records_timing(self):
        handler = TimingCallbackHandler()
        rid = _uid()

        handler.on_chain_start(
            _chain_serialized("Bull Researcher"), inputs={}, run_id=rid
        )
        time.sleep(0.01)
        handler.on_chain_end(outputs={}, run_id=rid)

        assert len(handler.chain_records) == 1
        record = handler.chain_records[0]
        assert record.name == "Bull Researcher"
        assert record.duration_s >= 0.01
        assert record.error is None

    def test_chain_error_records_error(self):
        handler = TimingCallbackHandler()
        rid = _uid()

        handler.on_chain_start(
            _chain_serialized("Trader"), inputs={}, run_id=rid
        )
        handler.on_chain_error(RuntimeError("timeout"), run_id=rid)

        assert len(handler.chain_records) == 1
        assert handler.chain_records[0].error == "timeout"

    def test_chain_end_without_start_is_ignored(self):
        handler = TimingCallbackHandler()
        handler.on_chain_end(outputs={}, run_id=_uid())
        assert len(handler.chain_records) == 0


class TestToolCallbacks:
    def test_tool_start_end_records_timing(self):
        handler = TimingCallbackHandler()
        rid = _uid()

        handler.on_tool_start(
            _tool_serialized("get_indicators"), input_str="AAPL", run_id=rid
        )
        time.sleep(0.01)
        handler.on_tool_end(output="data", run_id=rid)

        assert len(handler.tool_calls) == 1
        record = handler.tool_calls[0]
        assert record.tool_name == "get_indicators"
        assert record.duration_s >= 0.01
        assert record.error is None

    def test_tool_error_records_error(self):
        handler = TimingCallbackHandler()
        rid = _uid()

        handler.on_tool_start(
            _tool_serialized("get_news"), input_str="", run_id=rid
        )
        handler.on_tool_error(ConnectionError("API down"), run_id=rid)

        assert len(handler.tool_calls) == 1
        assert handler.tool_calls[0].error == "API down"


class TestSummaryAndReset:
    def test_get_summary_structure(self):
        handler = TimingCallbackHandler()
        rid = _uid()

        handler.on_chat_model_start(
            _serialized("gemini"), messages=[[]], run_id=rid
        )
        handler.on_llm_end(_llm_result_openai(10, 5, 15), run_id=rid)

        summary = handler.get_summary()
        assert "llm_calls" in summary
        assert "chain_records" in summary
        assert "tool_calls" in summary
        assert "totals" in summary

        totals = summary["totals"]
        assert totals["llm_call_count"] == 1
        assert totals["llm_total_tokens"] == 15
        assert totals["llm_total_input_tokens"] == 10
        assert totals["llm_total_output_tokens"] == 5

    def test_reset_clears_all(self):
        handler = TimingCallbackHandler()
        rid = _uid()

        handler.on_chat_model_start(
            _serialized(), messages=[[]], run_id=rid
        )
        handler.on_llm_end(_llm_result_openai(), run_id=rid)

        handler.on_chain_start(
            _chain_serialized(), inputs={}, run_id=_uid()
        )

        handler.reset()

        assert len(handler.llm_calls) == 0
        assert len(handler.chain_records) == 0
        assert len(handler.tool_calls) == 0
        summary = handler.get_summary()
        assert summary["totals"]["llm_call_count"] == 0

    def test_log_summary_does_not_raise(self, caplog):
        import logging

        handler = TimingCallbackHandler()
        rid = _uid()

        handler.on_chat_model_start(
            _serialized("test-model"), messages=[[]], run_id=rid
        )
        handler.on_llm_end(_llm_result_openai(), run_id=rid)

        with caplog.at_level(logging.INFO):
            handler.log_summary(end_to_end_s=5.0)

        assert "TradingAgents Execution Timing" in caplog.text


class TestThreadSafety:
    def test_concurrent_llm_calls(self):
        handler = TimingCallbackHandler()
        errors = []

        def simulate_llm_call():
            try:
                rid = _uid()
                handler.on_chat_model_start(
                    _serialized("concurrent-model"), messages=[[]], run_id=rid
                )
                time.sleep(0.001)
                handler.on_llm_end(_llm_result_openai(10, 5, 15), run_id=rid)
            except Exception as e:
                errors.append(e)

        threads = [threading.Thread(target=simulate_llm_call) for _ in range(20)]
        for t in threads:
            t.start()
        for t in threads:
            t.join()

        assert len(errors) == 0
        assert len(handler.llm_calls) == 20


class TestHelpers:
    def test_extract_model_name_from_kwargs(self):
        name = TimingCallbackHandler._extract_model_name(
            {"kwargs": {"model": "gpt-4o"}}
        )
        assert name == "gpt-4o"

    def test_extract_model_name_from_id(self):
        name = TimingCallbackHandler._extract_model_name(
            {"id": ["langchain", "ChatOpenAI"]}
        )
        assert name == "ChatOpenAI"

    def test_extract_model_name_fallback(self):
        name = TimingCallbackHandler._extract_model_name({})
        assert name == "unknown"

    def test_extract_chain_name_from_name(self):
        name = TimingCallbackHandler._extract_chain_name({"name": "Market Analyst"})
        assert name == "Market Analyst"

    def test_extract_chain_name_from_id(self):
        name = TimingCallbackHandler._extract_chain_name(
            {"id": ["langgraph", "StateGraph"]}
        )
        assert name == "StateGraph"

    def test_extract_tool_name(self):
        name = TimingCallbackHandler._extract_tool_name({"name": "get_news"})
        assert name == "get_news"

    def test_extract_tool_name_fallback(self):
        name = TimingCallbackHandler._extract_tool_name({})
        assert name == "unknown_tool"
