from typing import List, Optional

from fastapi import APIRouter, Query

from app.core.news.schemas import ArticlesListResponse, NewsSummaryResponse
from app.core.news.service import get_articles, get_summary

router = APIRouter()


@router.get("/articles", response_model=ArticlesListResponse)
def list_articles(
    keyword: Optional[List[str]] = Query(default=None),
    source: Optional[str] = Query(default=None),
    limit: int = Query(default=20, ge=1, le=100),
    offset: int = Query(default=0, ge=0),
):
    articles, total = get_articles(
        keywords=keyword, source=source, limit=limit, offset=offset
    )
    return ArticlesListResponse(
        articles=[article.model_dump() for article in articles],
        total=total,
    )


@router.get("/summary", response_model=NewsSummaryResponse)
def news_summary():
    return get_summary()
