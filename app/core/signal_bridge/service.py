from datetime import datetime, timezone

from app.core.news.service import get_articles, get_articles_by_ids
from app.core.signal_bridge.models import SignalGenerationRequest
from app.core.strategy.models import MarketSignal, SuggestedVendor

FOCUS_AREA_MAPPINGS = {
    "AI/Tech": {
        "tickers": ["NVDA", "MSFT", "GOOGL"],
        "keywords": ["AI", "artificial intelligence", "tech", "semiconductor", "GPU", "chip"],
    },
    "Chinese Markets": {
        "tickers": ["Xiaomi", "BABA", "BYD"],
        "keywords": ["China", "Chinese", "Xiaomi", "Alibaba", "BYD", "Huawei"],
    },
    "Macro": {
        "tickers": ["SPY", "TLT"],
        "keywords": ["macro", "Federal Reserve", "inflation", "GDP", "employment", "treasury"],
    },
    "Crypto": {
        "tickers": ["BTC-USD", "COIN"],
        "keywords": ["crypto", "Bitcoin", "blockchain", "Ethereum", "DeFi"],
    },
}


def generate_market_signal(request: SignalGenerationRequest) -> MarketSignal:
    mapping = FOCUS_AREA_MAPPINGS.get(request.focus_area or "", {})
    keywords = mapping.get("keywords", [])
    tickers = mapping.get("tickers", [])

    if request.article_ids:
        articles = get_articles_by_ids(request.article_ids)
    else:
        articles, _ = get_articles(keywords=keywords or None, limit=50)

    tickers = tickers[: request.max_vendors]

    article_ids = [a.id for a in articles]

    # Calculate confidence
    confidence = 0.5
    if len(articles) > 10:
        confidence += 0.1
    if len(articles) > 25:
        confidence += 0.1

    now = datetime.now(timezone.utc)
    for article in articles:
        if article.published_at and (now - article.published_at).total_seconds() < 86400:
            confidence += 0.1
            break

    confidence = min(confidence, 0.95)

    suggested_vendors = [
        SuggestedVendor(
            name=ticker,
            reason=f"Related to {request.focus_area or 'general'} focus area",
            confidence=confidence,
            supporting_articles=article_ids[:10],
        )
        for ticker in tickers
    ]

    return MarketSignal(
        signal_type=request.signal_type,
        label=request.focus_area or "General",
        confidence=confidence,
        supporting_articles=article_ids,
        suggested_vendors=suggested_vendors,
    )
