from typing import Literal

from pydantic import BaseModel


class SignalGenerationRequest(BaseModel):
    focus_area: str | None = None
    article_ids: list[int] = []
    signal_type: Literal["trend", "opportunity", "risk", "alert"] = "opportunity"
    max_vendors: int = 3
