from __future__ import annotations

from pydantic import BaseModel


class ModelSelectionRequest(BaseModel):
    quick_provider: str | None = None
    quick_model: str | None = None
    quick_backend_url: str | None = None
    deep_provider: str | None = None
    deep_model: str | None = None
    deep_backend_url: str | None = None
    google_thinking_level: str | None = None
    openai_reasoning_effort: str | None = None
