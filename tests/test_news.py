from unittest.mock import patch

from fastapi.testclient import TestClient

from app.core.news.models import NewsArticle
from app.main import app

client = TestClient(app)


def _mock_articles():
    return [
        NewsArticle(
            id=1,
            title="Anthropic raises funding",
            content="Anthropic announced new funding round.",
            link="https://example.com/1",
            published_at="2026-01-15T10:00:00Z",
            source="TechCrunch",
            topic="AI",
            subtopic="Funding",
        ),
        NewsArticle(
            id=2,
            title="OpenAI launches new model",
            content="OpenAI released a new model today.",
            link="https://example.com/2",
            published_at="2026-01-14T10:00:00Z",
            source="The Verge",
            topic="AI",
            subtopic="Models",
        ),
    ]


@patch("app.core.news.router.get_articles")
def test_list_articles(mock_get):
    mock_get.return_value = (_mock_articles(), 2)
    response = client.get("/api/news/articles?keyword=anthropic&limit=10&offset=0")
    assert response.status_code == 200
    data = response.json()
    assert data["total"] == 2
    assert len(data["articles"]) == 2
    assert data["articles"][0]["title"] == "Anthropic raises funding"


@patch("app.core.news.router.get_articles")
def test_list_articles_empty(mock_get):
    mock_get.return_value = ([], 0)
    response = client.get("/api/news/articles?keyword=nonexistent")
    assert response.status_code == 200
    data = response.json()
    assert data["total"] == 0
    assert data["articles"] == []


@patch("app.core.news.router.get_summary")
def test_news_summary(mock_summary):
    mock_summary.return_value = {
        "total_count": 501,
        "by_source": {"TechCrunch": 20, "reuters": 196},
        "latest_at": "2026-02-09T18:00:00Z",
    }
    response = client.get("/api/news/summary")
    assert response.status_code == 200
    data = response.json()
    assert data["total_count"] == 501
    assert "TechCrunch" in data["by_source"]
    assert data["latest_at"] is not None
