"""
NexusTrade — News Aggregator
Combines news from Alpha Vantage and Finnhub into a unified feed.
Deduplicates, normalizes sentiment, and enriches with social data.
"""

import logging
from dataclasses import dataclass, field
from difflib import SequenceMatcher

from data.stock_provider import StockProvider
from data.finnhub_provider import FinnhubProvider
from config import NEWS_MAX_ARTICLES

logger = logging.getLogger("nexustrade.news_aggregator")


@dataclass
class NewsBundle:
    """Unified news bundle from all sources."""
    ticker: str
    articles: list[dict] = field(default_factory=list)
    social_sentiment: dict = field(default_factory=dict)
    earnings_surprises: list[dict] = field(default_factory=list)
    recommendation_trends: list[dict] = field(default_factory=list)
    insider_transactions: list[dict] = field(default_factory=list)
    source_counts: dict = field(default_factory=dict)


class NewsAggregator:
    """Merges news from Alpha Vantage + Finnhub. Deduplicates and normalizes."""

    def __init__(self):
        self.stock_provider = StockProvider()
        self.finnhub = FinnhubProvider()

    def get_full_news_bundle(self, ticker: str) -> NewsBundle:
        """Fetch and merge news from all sources into a unified bundle.

        Args:
            ticker: Stock symbol (e.g. 'AAPL')

        Returns:
            NewsBundle with deduplicated articles, sentiment, earnings, etc.
        """
        bundle = NewsBundle(ticker=ticker)

        # ─── 1. Fetch articles from both sources ──────────────
        av_articles = self._fetch_alpha_vantage(ticker)
        fh_articles = self._fetch_finnhub(ticker)

        # Merge and deduplicate
        all_articles = av_articles + fh_articles
        bundle.articles = self._deduplicate(all_articles)[:NEWS_MAX_ARTICLES]

        bundle.source_counts = {
            "alpha_vantage": len(av_articles),
            "finnhub": len(fh_articles),
            "total_raw": len(all_articles),
            "after_dedup": len(bundle.articles),
        }

        logger.info(
            f"📰 News for {ticker}: {bundle.source_counts['alpha_vantage']} AV + "
            f"{bundle.source_counts['finnhub']} FH → {bundle.source_counts['after_dedup']} unique"
        )

        # ─── 2. Social sentiment (Finnhub) ────────────────────
        try:
            bundle.social_sentiment = self.finnhub.get_sentiment(ticker)
        except Exception as e:
            logger.warning(f"Social sentiment fetch failed: {e}")

        # ─── 3. Earnings surprises (Finnhub) ──────────────────
        try:
            bundle.earnings_surprises = self.finnhub.get_earnings_surprises(ticker)
        except Exception as e:
            logger.warning(f"Earnings fetch failed: {e}")

        # ─── 4. Recommendation trends (Finnhub) ──────────────
        try:
            bundle.recommendation_trends = self.finnhub.get_recommendation_trends(ticker)
        except Exception as e:
            logger.warning(f"Recommendations fetch failed: {e}")

        # ─── 5. Insider transactions (Alpha Vantage) ──────────
        try:
            bundle.insider_transactions = self.stock_provider.get_insider_transactions(ticker)
        except Exception as e:
            logger.warning(f"Insider transactions fetch failed: {e}")

        return bundle

    def _fetch_alpha_vantage(self, ticker: str) -> list[dict]:
        """Fetch news from Alpha Vantage."""
        try:
            articles = self.stock_provider.get_news(ticker)
            for a in articles:
                a["source_provider"] = "alpha_vantage"
                a["overall_sentiment"] = self._normalize_sentiment(
                    a.get("overall_sentiment", "")
                )
            return articles
        except Exception as e:
            logger.warning(f"Alpha Vantage news fetch failed: {e}")
            return []

    def _fetch_finnhub(self, ticker: str) -> list[dict]:
        """Fetch news from Finnhub."""
        try:
            return self.finnhub.get_company_news(ticker)
        except Exception as e:
            logger.warning(f"Finnhub news fetch failed: {e}")
            return []

    def _deduplicate(self, articles: list[dict]) -> list[dict]:
        """Remove near-duplicate articles based on title similarity."""
        if not articles:
            return []

        unique = []
        seen_titles = []

        for article in articles:
            title = article.get("title", "").strip()
            if not title:
                continue

            is_dupe = False
            for seen in seen_titles:
                similarity = SequenceMatcher(None, title.lower(), seen.lower()).ratio()
                if similarity > 0.75:
                    is_dupe = True
                    break

            if not is_dupe:
                unique.append(article)
                seen_titles.append(title)

        return unique

    @staticmethod
    def _normalize_sentiment(label: str) -> str:
        """Normalize sentiment labels across providers."""
        label = label.lower().strip()
        if any(w in label for w in ["bullish", "positive", "somewhat_bullish"]):
            return "Bullish"
        elif any(w in label for w in ["bearish", "negative", "somewhat_bearish"]):
            return "Bearish"
        elif any(w in label for w in ["neutral", "mixed"]):
            return "Neutral"
        return label.title() if label else "Unknown"
