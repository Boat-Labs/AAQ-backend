from datetime import datetime
from typing import Optional

from pydantic import BaseModel


class NewsArticle(BaseModel):
    id: int
    title: str
    content: Optional[str] = None
    link: Optional[str] = None
    published_at: Optional[datetime] = None
    source: Optional[str] = None
    author: Optional[str] = None
    topic: Optional[str] = None
    subtopic: Optional[str] = None
    content_type: Optional[str] = None
    created_at: Optional[datetime] = None
