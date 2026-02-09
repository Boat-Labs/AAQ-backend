from datetime import datetime
from typing import Dict, List, Optional

from pydantic import BaseModel


class ArticleResponse(BaseModel):
    id: int
    title: str
    content: Optional[str] = None
    link: Optional[str] = None
    published_at: Optional[datetime] = None
    source: Optional[str] = None
    topic: Optional[str] = None
    subtopic: Optional[str] = None


class ArticlesListResponse(BaseModel):
    articles: List[ArticleResponse]
    total: int


class NewsSummaryResponse(BaseModel):
    total_count: int
    by_source: Dict[str, int]
    latest_at: Optional[datetime] = None
