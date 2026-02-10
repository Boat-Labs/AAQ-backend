from pydantic import BaseModel


class SignalGenerationRequest(BaseModel):
    focus_area: str | None = None
    article_ids: list[int] = []
    signal_type: str = "opportunity"
    max_vendors: int = 3
