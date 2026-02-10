from typing import Any, Optional
import importlib.metadata
import warnings

from langchain_google_genai import ChatGoogleGenerativeAI
import langchain_google_genai.chat_models as gm
from langchain_core.messages import AIMessage, HumanMessage, SystemMessage, ToolMessage, FunctionMessage

from .base_client import BaseLLMClient
from .validators import validate_model


def _version_tuple(version_str: str) -> tuple[int, ...]:
    parts = []
    for token in version_str.split("."):
        num = ""
        for ch in token:
            if ch.isdigit():
                num += ch
            else:
                break
        if num:
            parts.append(int(num))
    return tuple(parts) if parts else (0,)


def _apply_google_thought_signature_patch() -> None:
    """Patch langchain-google-genai <=2.1.5 to round-trip thought_signature.

    In these versions, tool-call messages are reconstructed without thought_signature,
    which causes Gemini 2.5/3 tool workflows to fail with:
    "function call is missing a thought_signature".
    """
    if getattr(gm, "_ta_thought_signature_patch_applied", False):
        return

    try:
        version = importlib.metadata.version("langchain-google-genai")
    except Exception:
        version = "0.0.0"

    if _version_tuple(version) > (2, 1, 5):
        return

    original_parse_response_candidate = gm._parse_response_candidate

    function_call_fields = []
    try:
        function_call_fields = [f.name for f in gm.FunctionCall()._pb.DESCRIPTOR.fields]
    except Exception:
        function_call_fields = []
    function_call_supports_thought_signature = "thought_signature" in function_call_fields

    def patched_parse_response_candidate(response_candidate, streaming: bool = False):
        message = original_parse_response_candidate(response_candidate, streaming=streaming)
        if streaming:
            return message

        signatures = []
        try:
            for part in response_candidate.content.parts:
                if getattr(part, "function_call", None):
                    signatures.append(getattr(part, "thought_signature", None))
        except Exception:
            signatures = []

        if signatures and isinstance(message, AIMessage):
            additional_kwargs = dict(message.additional_kwargs or {})
            additional_kwargs["_function_call_thought_signatures"] = signatures
            message.additional_kwargs = additional_kwargs
        return message

    def patched_parse_chat_history(
        input_messages,
        convert_system_message_to_human: bool = False,
    ):
        messages = []

        if convert_system_message_to_human:
            warnings.warn("Convert_system_message_to_human will be deprecated!")

        system_instruction = None
        messages_without_tool_messages = [
            message for message in input_messages if not isinstance(message, ToolMessage)
        ]
        tool_messages = [
            message for message in input_messages if isinstance(message, ToolMessage)
        ]

        for i, message in enumerate(messages_without_tool_messages):
            if isinstance(message, SystemMessage):
                system_parts = gm._convert_to_parts(message.content)
                if i == 0:
                    system_instruction = gm.Content(parts=system_parts)
                elif system_instruction is not None:
                    system_instruction.parts.extend(system_parts)
                continue

            if isinstance(message, AIMessage):
                role = "model"
                if message.tool_calls:
                    if function_call_supports_thought_signature:
                        ai_message_parts = []
                        raw_signatures = (message.additional_kwargs or {}).get(
                            "_function_call_thought_signatures", []
                        )
                        for idx, tool_call in enumerate(message.tool_calls):
                            fc_payload = {
                                "name": tool_call["name"],
                                "args": tool_call["args"],
                            }
                            if idx < len(raw_signatures) and raw_signatures[idx]:
                                fc_payload["thought_signature"] = raw_signatures[idx]
                            function_call = gm.FunctionCall(fc_payload)
                            ai_message_parts.append(gm.Part(function_call=function_call))

                        tool_messages_parts = gm._get_ai_message_tool_messages_parts(
                            tool_messages=tool_messages, ai_message=message
                        )
                        messages.append(gm.Content(role=role, parts=ai_message_parts))
                        messages.append(gm.Content(role="user", parts=tool_messages_parts))
                    else:
                        # Compatibility fallback for old google proto schema that does not
                        # support function_call.thought_signature. We serialize prior
                        # tool calls/results as plain text instead of functionCall parts.
                        call_text = gm.json.dumps(
                            [{"name": tc.get("name"), "args": tc.get("args")} for tc in message.tool_calls],
                            ensure_ascii=False,
                        )
                        model_parts = gm._convert_to_parts(
                            f"Previous tool calls: {call_text}"
                        )
                        messages.append(gm.Content(role=role, parts=model_parts))

                        tool_result_lines = []
                        tool_calls_ids = {tc["id"]: tc for tc in message.tool_calls}
                        for tool_msg in tool_messages:
                            if tool_msg.tool_call_id in tool_calls_ids:
                                tc_name = tool_calls_ids[tool_msg.tool_call_id].get("name", "tool")
                                tool_result_lines.append(
                                    f"Tool result ({tc_name}): {tool_msg.content}"
                                )
                        user_parts = gm._convert_to_parts("\n\n".join(tool_result_lines))
                        messages.append(gm.Content(role="user", parts=user_parts))
                    continue

                if raw_function_call := message.additional_kwargs.get("function_call"):
                    function_call = gm.FunctionCall(
                        {
                            "name": raw_function_call["name"],
                            "args": gm.json.loads(raw_function_call["arguments"]),
                        }
                    )
                    parts = [gm.Part(function_call=function_call)]
                else:
                    parts = gm._convert_to_parts(message.content)

            elif isinstance(message, HumanMessage):
                role = "user"
                parts = gm._convert_to_parts(message.content)
                if i == 1 and convert_system_message_to_human and system_instruction:
                    parts = [p for p in system_instruction.parts] + parts
                    system_instruction = None

            elif isinstance(message, FunctionMessage):
                role = "user"
                parts = gm._convert_tool_message_to_parts(message)
            else:
                raise ValueError(
                    f"Unexpected message with type {type(message)} at the position {i}."
                )

            messages.append(gm.Content(role=role, parts=parts))

        return system_instruction, messages

    gm._parse_response_candidate = patched_parse_response_candidate
    gm._parse_chat_history = patched_parse_chat_history
    gm._ta_thought_signature_patch_applied = True


_apply_google_thought_signature_patch()


class NormalizedChatGoogleGenerativeAI(ChatGoogleGenerativeAI):
    """Wrapper for ChatGoogleGenerativeAI.

    NOTE:
    Do not normalize/flatten Gemini structured `content` parts here.
    Tool-calling flows can depend on provider-specific metadata (e.g.
    thought signatures) carried in structured parts between turns.
    """

    def _normalize_content(self, response):
        return response

    def invoke(self, input, config=None, **kwargs):
        return self._normalize_content(super().invoke(input, config, **kwargs))


class GoogleClient(BaseLLMClient):
    """Client for Google Gemini models."""

    def __init__(self, model: str, base_url: Optional[str] = None, **kwargs):
        super().__init__(model, base_url, **kwargs)

    @staticmethod
    def _supports_param(param_name: str) -> bool:
        """Check whether ChatGoogleGenerativeAI accepts a constructor parameter.

        Handles both pydantic v2 (`model_fields`) and v1 (`__fields__`).
        """
        model_fields = getattr(ChatGoogleGenerativeAI, "model_fields", None)
        if isinstance(model_fields, dict):
            return param_name in model_fields

        legacy_fields = getattr(ChatGoogleGenerativeAI, "__fields__", None)
        if isinstance(legacy_fields, dict):
            return param_name in legacy_fields

        return False

    def get_llm(self) -> Any:
        """Return configured ChatGoogleGenerativeAI instance."""
        llm_kwargs = {"model": self.model}

        for key in ("timeout", "max_retries", "google_api_key", "callbacks"):
            if key in self.kwargs:
                llm_kwargs[key] = self.kwargs[key]

        # Keep hidden reasoning payloads disabled by default in tool pipelines.
        if self._supports_param("include_thoughts"):
            llm_kwargs["include_thoughts"] = False

        # Map thinking configuration to whichever parameter this installed
        # langchain-google-genai version supports.
        thinking_level = self.kwargs.get("thinking_level")
        supports_thinking_level = self._supports_param("thinking_level")
        supports_thinking_budget = self._supports_param("thinking_budget")

        if thinking_level:
            model_lower = self.model.lower()

            if supports_thinking_level:
                # Gemini 3 Pro doesn't support "minimal", use "low" instead
                if "gemini-3" in model_lower and "pro" in model_lower and thinking_level == "minimal":
                    thinking_level = "low"
                llm_kwargs["thinking_level"] = thinking_level
            elif supports_thinking_budget:
                llm_kwargs["thinking_budget"] = -1 if thinking_level == "high" else 0
        elif supports_thinking_budget:
            # Keep model default when no explicit mode is requested.
            pass

        return NormalizedChatGoogleGenerativeAI(**llm_kwargs)

    def validate_model(self) -> bool:
        """Validate model for Google."""
        return validate_model("google", self.model)
