from __future__ import annotations

from pydantic import BaseModel, field_validator

from app.core.tradingagents.llm_clients.validators import VALID_MODELS

_VALID_PROVIDERS = set(VALID_MODELS.keys()) | {"ollama", "openrouter"}


class ModelSelectionRequest(BaseModel):
    quick_provider: str | None = None
    quick_model: str | None = None
    quick_backend_url: str | None = None
    deep_provider: str | None = None
    deep_model: str | None = None
    deep_backend_url: str | None = None
    google_thinking_level: str | None = None
    openai_reasoning_effort: str | None = None

    @field_validator("quick_provider", "deep_provider")
    @classmethod
    def validate_provider(cls, v: str | None) -> str | None:
        if v is None:
            return v
        v = v.strip().lower()
        if v not in _VALID_PROVIDERS:
            raise ValueError(
                f"Unknown provider '{v}'. Valid: {sorted(_VALID_PROVIDERS)}"
            )
        return v

    @field_validator("google_thinking_level")
    @classmethod
    def validate_thinking_level(cls, v: str | None) -> str | None:
        if v is None:
            return v
        v = v.strip().lower()
        if v not in {"high", "minimal"}:
            raise ValueError("google_thinking_level must be 'high' or 'minimal'")
        return v

    @field_validator("quick_backend_url", "deep_backend_url")
    @classmethod
    def validate_backend_url(cls, v: str | None) -> str | None:
        if v is None:
            return v
        if not v.startswith("https://"):
            raise ValueError("backend_url must use HTTPS")
        return v

    @field_validator("openai_reasoning_effort")
    @classmethod
    def validate_reasoning_effort(cls, v: str | None) -> str | None:
        if v is None:
            return v
        v = v.strip().lower()
        if v not in {"low", "medium", "high"}:
            raise ValueError(
                "openai_reasoning_effort must be 'low', 'medium', or 'high'"
            )
        return v
