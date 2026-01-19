from datetime import datetime
from typing import List

from pydantic import BaseModel


class Signal(BaseModel):
    name: str
    value: float


class Event(BaseModel):
    event_type: str
    description: str
    timestamp: datetime


class MarketSnapshot(BaseModel):
    symbols: List[str]
    signals: List[Signal]
    events: List[Event]
