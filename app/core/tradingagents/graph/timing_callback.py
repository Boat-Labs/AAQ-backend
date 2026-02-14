"""Observability callback handler for TradingAgents execution timing.

Captures per-LLM-call latency, token usage, per-node/chain latency,
per-tool-call latency, and end-to-end total time.
"""

import logging
import threading
import time
from dataclasses import dataclass
from typing import Any, Dict, List, Optional
from uuid import UUID

from langchain_core.callbacks import BaseCallbackHandler
from langchain_core.messages import BaseMessage
from langchain_core.outputs import LLMResult

logger = logging.getLogger(__name__)


@dataclass
class LLMCallRecord:
    """Record of a single LLM invocation."""

    run_id: str
    model: str
    start_time: float
    end_time: float = 0.0
    duration_s: float = 0.0
    input_tokens: int = 0
    output_tokens: int = 0
    total_tokens: int = 0
    error: Optional[str] = None


@dataclass
class ChainRecord:
    """Record of a chain/node execution."""

    run_id: str
    name: str
    parent_run_id: Optional[str] = None
    start_time: float = 0.0
    end_time: float = 0.0
    duration_s: float = 0.0
    error: Optional[str] = None


@dataclass
class ToolCallRecord:
    """Record of a tool invocation."""

    run_id: str
    tool_name: str
    start_time: float = 0.0
    end_time: float = 0.0
    duration_s: float = 0.0
    error: Optional[str] = None


class TimingCallbackHandler(BaseCallbackHandler):
    """Thread-safe callback handler that tracks execution timing and token usage.

    Collects:
    - Per-LLM-call: latency, model name, input/output/total tokens
    - Per-chain/node: latency, node name, parent-child relationships
    - Per-tool-call: latency, tool name
    - Summaries via get_summary()

    Thread-safety: All mutable state is protected by a threading.Lock.
    """

    def __init__(self) -> None:
        super().__init__()
        self._lock = threading.Lock()

        # In-flight tracking (keyed by run_id str)
        self._llm_starts: Dict[str, float] = {}
        self._llm_serialized: Dict[str, Dict] = {}
        self._chain_starts: Dict[str, ChainRecord] = {}
        self._tool_starts: Dict[str, float] = {}
        self._tool_serialized: Dict[str, Dict] = {}

        # Completed records
        self.llm_calls: List[LLMCallRecord] = []
        self.chain_records: List[ChainRecord] = []
        self.tool_calls: List[ToolCallRecord] = []

    # ── Helpers ──────────────────────────────────────────────

    @staticmethod
    def _extract_model_name(serialized: Dict[str, Any]) -> str:
        kwargs = serialized.get("kwargs", {})
        model = kwargs.get("model") or kwargs.get("model_name", "")
        if model:
            return model
        id_list = serialized.get("id", [])
        return id_list[-1] if id_list else "unknown"

    @staticmethod
    def _extract_tool_name(serialized: Dict[str, Any]) -> str:
        return serialized.get("name", "unknown_tool")

    @staticmethod
    def _extract_chain_name(serialized: Dict[str, Any]) -> str:
        name = serialized.get("name")
        if name:
            return name
        id_list = serialized.get("id", [])
        return id_list[-1] if id_list else "unknown_chain"

    @staticmethod
    def _extract_token_usage(response: LLMResult) -> Dict[str, int]:
        """Extract token usage from LLMResult.

        Tries two paths:
        1. response.llm_output["token_usage"] (OpenAI style)
        2. generation.message.usage_metadata (LangChain standard)
        """
        result = {"input_tokens": 0, "output_tokens": 0, "total_tokens": 0}

        if response.llm_output:
            token_usage = response.llm_output.get("token_usage", {})
            if token_usage:
                result["input_tokens"] = token_usage.get("prompt_tokens", 0)
                result["output_tokens"] = token_usage.get("completion_tokens", 0)
                result["total_tokens"] = token_usage.get("total_tokens", 0)
                return result

        if response.generations:
            for gen_list in response.generations:
                for gen in gen_list:
                    msg = getattr(gen, "message", None)
                    usage = getattr(msg, "usage_metadata", None) if msg else None
                    if usage:
                        result["input_tokens"] = usage.get("input_tokens", 0)
                        result["output_tokens"] = usage.get("output_tokens", 0)
                        result["total_tokens"] = usage.get("total_tokens", 0)
                        return result

        return result

    # ── LLM Callbacks ────────────────────────────────────────

    def on_chat_model_start(
        self,
        serialized: Dict[str, Any],
        messages: List[List[BaseMessage]],
        *,
        run_id: UUID,
        parent_run_id: Optional[UUID] = None,
        tags: Optional[List[str]] = None,
        metadata: Optional[Dict[str, Any]] = None,
        **kwargs: Any,
    ) -> None:
        rid = str(run_id)
        with self._lock:
            self._llm_starts[rid] = time.monotonic()
            self._llm_serialized[rid] = serialized

    def on_llm_start(
        self,
        serialized: Dict[str, Any],
        prompts: List[str],
        *,
        run_id: UUID,
        parent_run_id: Optional[UUID] = None,
        tags: Optional[List[str]] = None,
        metadata: Optional[Dict[str, Any]] = None,
        **kwargs: Any,
    ) -> None:
        rid = str(run_id)
        with self._lock:
            self._llm_starts[rid] = time.monotonic()
            self._llm_serialized[rid] = serialized

    def on_llm_end(
        self,
        response: LLMResult,
        *,
        run_id: UUID,
        parent_run_id: Optional[UUID] = None,
        tags: Optional[List[str]] = None,
        **kwargs: Any,
    ) -> None:
        rid = str(run_id)
        end_time = time.monotonic()
        with self._lock:
            start_time = self._llm_starts.pop(rid, end_time)
            serialized = self._llm_serialized.pop(rid, {})

        tokens = self._extract_token_usage(response)
        record = LLMCallRecord(
            run_id=rid,
            model=self._extract_model_name(serialized),
            start_time=start_time,
            end_time=end_time,
            duration_s=end_time - start_time,
            input_tokens=tokens["input_tokens"],
            output_tokens=tokens["output_tokens"],
            total_tokens=tokens["total_tokens"],
        )
        with self._lock:
            self.llm_calls.append(record)

        logger.debug(
            "LLM call completed: model=%s duration=%.2fs tokens=%d",
            record.model,
            record.duration_s,
            record.total_tokens,
        )

    def on_llm_error(
        self,
        error: BaseException,
        *,
        run_id: UUID,
        parent_run_id: Optional[UUID] = None,
        tags: Optional[List[str]] = None,
        **kwargs: Any,
    ) -> None:
        rid = str(run_id)
        end_time = time.monotonic()
        with self._lock:
            start_time = self._llm_starts.pop(rid, end_time)
            serialized = self._llm_serialized.pop(rid, {})

        record = LLMCallRecord(
            run_id=rid,
            model=self._extract_model_name(serialized),
            start_time=start_time,
            end_time=end_time,
            duration_s=end_time - start_time,
            error=str(error),
        )
        with self._lock:
            self.llm_calls.append(record)

    # ── Chain / Node Callbacks ───────────────────────────────

    def on_chain_start(
        self,
        serialized: Dict[str, Any],
        inputs: Dict[str, Any],
        *,
        run_id: UUID,
        parent_run_id: Optional[UUID] = None,
        tags: Optional[List[str]] = None,
        metadata: Optional[Dict[str, Any]] = None,
        **kwargs: Any,
    ) -> None:
        rid = str(run_id)
        record = ChainRecord(
            run_id=rid,
            name=self._extract_chain_name(serialized),
            parent_run_id=str(parent_run_id) if parent_run_id else None,
            start_time=time.monotonic(),
        )
        with self._lock:
            self._chain_starts[rid] = record

    def on_chain_end(
        self,
        outputs: Dict[str, Any],
        *,
        run_id: UUID,
        parent_run_id: Optional[UUID] = None,
        **kwargs: Any,
    ) -> None:
        rid = str(run_id)
        end_time = time.monotonic()
        with self._lock:
            record = self._chain_starts.pop(rid, None)
        if record:
            record.end_time = end_time
            record.duration_s = end_time - record.start_time
            with self._lock:
                self.chain_records.append(record)
            logger.debug(
                "Chain/node completed: name=%s duration=%.2fs",
                record.name,
                record.duration_s,
            )

    def on_chain_error(
        self,
        error: BaseException,
        *,
        run_id: UUID,
        parent_run_id: Optional[UUID] = None,
        **kwargs: Any,
    ) -> None:
        rid = str(run_id)
        end_time = time.monotonic()
        with self._lock:
            record = self._chain_starts.pop(rid, None)
        if record:
            record.end_time = end_time
            record.duration_s = end_time - record.start_time
            record.error = str(error)
            with self._lock:
                self.chain_records.append(record)

    # ── Tool Callbacks ───────────────────────────────────────

    def on_tool_start(
        self,
        serialized: Dict[str, Any],
        input_str: str,
        *,
        run_id: UUID,
        parent_run_id: Optional[UUID] = None,
        tags: Optional[List[str]] = None,
        metadata: Optional[Dict[str, Any]] = None,
        **kwargs: Any,
    ) -> None:
        rid = str(run_id)
        with self._lock:
            self._tool_starts[rid] = time.monotonic()
            self._tool_serialized[rid] = serialized

    def on_tool_end(
        self,
        output: Any,
        *,
        run_id: UUID,
        parent_run_id: Optional[UUID] = None,
        **kwargs: Any,
    ) -> None:
        rid = str(run_id)
        end_time = time.monotonic()
        with self._lock:
            start_time = self._tool_starts.pop(rid, end_time)
            serialized = self._tool_serialized.pop(rid, {})

        record = ToolCallRecord(
            run_id=rid,
            tool_name=self._extract_tool_name(serialized),
            start_time=start_time,
            end_time=end_time,
            duration_s=end_time - start_time,
        )
        with self._lock:
            self.tool_calls.append(record)

        logger.debug(
            "Tool call completed: name=%s duration=%.2fs",
            record.tool_name,
            record.duration_s,
        )

    def on_tool_error(
        self,
        error: BaseException,
        *,
        run_id: UUID,
        parent_run_id: Optional[UUID] = None,
        **kwargs: Any,
    ) -> None:
        rid = str(run_id)
        end_time = time.monotonic()
        with self._lock:
            start_time = self._tool_starts.pop(rid, end_time)
            serialized = self._tool_serialized.pop(rid, {})

        record = ToolCallRecord(
            run_id=rid,
            tool_name=self._extract_tool_name(serialized),
            start_time=start_time,
            end_time=end_time,
            duration_s=end_time - start_time,
            error=str(error),
        )
        with self._lock:
            self.tool_calls.append(record)

    # ── Summary / Report ─────────────────────────────────────

    def get_summary(self) -> Dict[str, Any]:
        """Return a structured summary of all captured timing data."""
        with self._lock:
            llm_calls = list(self.llm_calls)
            chains = list(self.chain_records)
            tools = list(self.tool_calls)

        total_llm_time = sum(c.duration_s for c in llm_calls)
        total_input_tokens = sum(c.input_tokens for c in llm_calls)
        total_output_tokens = sum(c.output_tokens for c in llm_calls)
        total_tokens = sum(c.total_tokens for c in llm_calls)
        total_tool_time = sum(t.duration_s for t in tools)

        return {
            "llm_calls": [
                {
                    "model": c.model,
                    "duration_s": round(c.duration_s, 3),
                    "input_tokens": c.input_tokens,
                    "output_tokens": c.output_tokens,
                    "total_tokens": c.total_tokens,
                    "error": c.error,
                }
                for c in llm_calls
            ],
            "chain_records": [
                {
                    "name": r.name,
                    "duration_s": round(r.duration_s, 3),
                    "error": r.error,
                }
                for r in chains
            ],
            "tool_calls": [
                {
                    "tool_name": t.tool_name,
                    "duration_s": round(t.duration_s, 3),
                    "error": t.error,
                }
                for t in tools
            ],
            "totals": {
                "llm_call_count": len(llm_calls),
                "llm_total_time_s": round(total_llm_time, 3),
                "llm_total_input_tokens": total_input_tokens,
                "llm_total_output_tokens": total_output_tokens,
                "llm_total_tokens": total_tokens,
                "tool_call_count": len(tools),
                "tool_total_time_s": round(total_tool_time, 3),
                "chain_count": len(chains),
            },
        }

    def log_summary(self, end_to_end_s: Optional[float] = None) -> None:
        """Log a human-readable summary at INFO level."""
        summary = self.get_summary()
        totals = summary["totals"]

        lines = ["=== TradingAgents Execution Timing ==="]
        if end_to_end_s is not None:
            lines.append(f"End-to-end wall time: {end_to_end_s:.2f}s")

        lines.append(
            f"LLM calls: {totals['llm_call_count']} | "
            f"Total LLM time: {totals['llm_total_time_s']:.2f}s | "
            f"Tokens: {totals['llm_total_tokens']} "
            f"(in={totals['llm_total_input_tokens']}, "
            f"out={totals['llm_total_output_tokens']})"
        )
        lines.append(
            f"Tool calls: {totals['tool_call_count']} | "
            f"Total tool time: {totals['tool_total_time_s']:.2f}s"
        )

        for i, call in enumerate(summary["llm_calls"], 1):
            status = f" ERROR: {call['error']}" if call["error"] else ""
            lines.append(
                f"  LLM #{i}: {call['model']} {call['duration_s']:.2f}s "
                f"tokens={call['total_tokens']}{status}"
            )

        for rec in summary["chain_records"]:
            status = f" ERROR: {rec['error']}" if rec["error"] else ""
            lines.append(f"  Node: {rec['name']} {rec['duration_s']:.2f}s{status}")

        for tc in summary["tool_calls"]:
            status = f" ERROR: {tc['error']}" if tc["error"] else ""
            lines.append(
                f"  Tool: {tc['tool_name']} {tc['duration_s']:.2f}s{status}"
            )

        logger.info("\n".join(lines))

    def reset(self) -> None:
        """Clear all collected data for reuse across multiple propagate() calls."""
        with self._lock:
            self._llm_starts.clear()
            self._llm_serialized.clear()
            self._chain_starts.clear()
            self._tool_starts.clear()
            self._tool_serialized.clear()
            self.llm_calls.clear()
            self.chain_records.clear()
            self.tool_calls.clear()
