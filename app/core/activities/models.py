from datetime import datetime

from pydantic import BaseModel


class Decision(BaseModel):
    decision_id: str
    user_id: str
    action: str
    timestamp: datetime


class Feedback(BaseModel):
    decision_id: str
    rating: int
    comment: str | None = None
