from typing import List, Optional, Tuple

import psycopg2
import psycopg2.extras

from app.core.news.models import NewsArticle
from app.core.shared.config import settings


def _get_connection():
    return psycopg2.connect(
        host=settings.database_host,
        port=settings.database_port,
        user=settings.database_user,
        password=settings.database_password,
        dbname=settings.database_name,
    )


def get_articles(
    keywords: Optional[List[str]] = None,
    source: Optional[str] = None,
    limit: int = 20,
    offset: int = 0,
) -> Tuple[List[NewsArticle], int]:
    conn = _get_connection()
    try:
        with conn.cursor(cursor_factory=psycopg2.extras.RealDictCursor) as cur:
            conditions = []
            params: list = []

            if keywords:
                keyword_conditions = []
                for kw in keywords:
                    keyword_conditions.append(
                        "(title ILIKE %s OR content ILIKE %s)"
                    )
                    params.extend([f"%{kw}%", f"%{kw}%"])
                conditions.append(f"({' OR '.join(keyword_conditions)})")

            if source:
                conditions.append("source = %s")
                params.append(source)

            where_clause = ""
            if conditions:
                where_clause = "WHERE " + " AND ".join(conditions)

            # Get total count
            count_query = f"SELECT COUNT(*) as total FROM public.news {where_clause}"
            cur.execute(count_query, params)
            total = cur.fetchone()["total"]

            # Get articles
            query = f"""
                SELECT id, title, content, link, published_at, source, author,
                       topic, subtopic, content_type, created_at
                FROM public.news
                {where_clause}
                ORDER BY published_at DESC NULLS LAST
                LIMIT %s OFFSET %s
            """
            cur.execute(query, params + [limit, offset])
            rows = cur.fetchall()

            articles = [NewsArticle(**row) for row in rows]
            return articles, total
    finally:
        conn.close()


def get_articles_by_ids(ids: list[int]) -> list[NewsArticle]:
    if not ids:
        return []
    conn = _get_connection()
    try:
        with conn.cursor(cursor_factory=psycopg2.extras.RealDictCursor) as cur:
            query = """
                SELECT id, title, content, link, published_at, source, author,
                       topic, subtopic, content_type, created_at
                FROM public.news
                WHERE id = ANY(%s)
                ORDER BY published_at DESC NULLS LAST
            """
            cur.execute(query, [ids])
            rows = cur.fetchall()
            return [NewsArticle(**row) for row in rows]
    finally:
        conn.close()


def get_summary() -> dict:
    conn = _get_connection()
    try:
        with conn.cursor(cursor_factory=psycopg2.extras.RealDictCursor) as cur:
            cur.execute("SELECT COUNT(*) as total FROM public.news")
            total_count = cur.fetchone()["total"]

            cur.execute(
                "SELECT source, COUNT(*) as count FROM public.news "
                "GROUP BY source ORDER BY count DESC"
            )
            by_source = {row["source"]: row["count"] for row in cur.fetchall()}

            cur.execute(
                "SELECT MAX(published_at) as latest FROM public.news"
            )
            latest_at = cur.fetchone()["latest"]

            return {
                "total_count": total_count,
                "by_source": by_source,
                "latest_at": latest_at,
            }
    finally:
        conn.close()
