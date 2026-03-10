"""
NexusTrade — Finnhub Data Provider
Wraps Finnhub's free API for company news, market news, sentiment, and earnings.
"""

import requests
import logging
from datetime import datetime, timedelta
from typing import Optional

from config import FINNHUB_API_KEY, NEWS_LOOKBACK_DAYS

logger = logging.getLogger("nexustrade.finnhub")

BASE_URL = "https://finnhub.io/api/v1"


class FinnhubProvider:
    """Fetches news, sentiment, and earnings data from Finnhub's free API."""

    def __init__(self, api_key: str = ""):
        self.api_key = api_key or FINNHUB_API_KEY
        if not self.api_key:
            logger.warning("⚠️ FINNHUB_API_KEY not set — Finnhub provider will return empty results")

    def _get(self, endpoint: str, params: dict = None) -> dict | list:
        """Make an authenticated GET request to Finnhub."""
        if not self.api_key:
            return []
        params = params or {}
        params["token"] = self.api_key
        try:
            resp = requests.get(f"{BASE_URL}/{endpoint}", params=params, timeout=10)
            resp.raise_for_status()
            return resp.json()
        except requests.exceptions.HTTPError as e:
            if resp.status_code == 429:
                logger.warning("⚠️ Finnhub rate limit hit")
            else:
                logger.error(f"Finnhub HTTP error: {e}")
            return []
        except Exception as e:
            logger.error(f"Finnhub request error: {e}")
            return []

    def get_company_news(
        self,
        ticker: str,
        from_date: Optional[str] = None,
        to_date: Optional[str] = None,
    ) -> list[dict]:
        """Get company-specific news articles.

        Returns up to 100 articles with headline, source, URL, datetime, summary.
        """
        if not to_date:
            to_date = datetime.utcnow().strftime("%Y-%m-%d")
        if not from_date:
            from_date = (datetime.utcnow() - timedelta(days=NEWS_LOOKBACK_DAYS)).strftime("%Y-%m-%d")

        data = self._get("company-news", {
            "symbol": ticker,
            "from": from_date,
            "to": to_date,
        })

        if not isinstance(data, list):
            return []

        articles = []
        for item in data[:50]:  # Cap at 50 per source
            articles.append({
                "title": item.get("headline", ""),
                "publisher": item.get("source", ""),
                "link": item.get("url", ""),
                "published": datetime.fromtimestamp(item.get("datetime", 0)).strftime("%Y-%m-%dT%H:%M:%S") if item.get("datetime") else "",
                "summary": item.get("summary", ""),
                "image": item.get("image", ""),
                "category": item.get("category", ""),
                "source_provider": "finnhub",
                "type": "news",
            })
        return articles

    def get_market_news(self, category: str = "general") -> list[dict]:
        """Get general market news.

        Categories: general, forex, crypto, merger
        """
        data = self._get("news", {"category": category})

        if not isinstance(data, list):
            return []

        articles = []
        for item in data[:20]:
            articles.append({
                "title": item.get("headline", ""),
                "publisher": item.get("source", ""),
                "link": item.get("url", ""),
                "published": datetime.fromtimestamp(item.get("datetime", 0)).strftime("%Y-%m-%dT%H:%M:%S") if item.get("datetime") else "",
                "summary": item.get("summary", ""),
                "category": category,
                "source_provider": "finnhub",
                "type": "market_news",
            })
        return articles

    def get_sentiment(self, ticker: str) -> dict:
        """Get social sentiment scores for a ticker.

        Returns insider sentiment + social media buzz metrics.
        """
        # Insider sentiment
        insider = self._get("stock/insider-sentiment", {
            "symbol": ticker,
            "from": (datetime.utcnow() - timedelta(days=90)).strftime("%Y-%m-%d"),
            "to": datetime.utcnow().strftime("%Y-%m-%d"),
        })

        # Social sentiment (Reddit + Twitter)
        social = self._get("stock/social-sentiment", {
            "symbol": ticker,
            "from": (datetime.utcnow() - timedelta(days=7)).strftime("%Y-%m-%d"),
            "to": datetime.utcnow().strftime("%Y-%m-%d"),
        })

        result = {
            "insider_sentiment": [],
            "social_sentiment": {
                "reddit": [],
                "twitter": [],
            },
        }

        # Parse insider sentiment
        if isinstance(insider, dict) and "data" in insider:
            for entry in insider["data"][-3:]:  # Last 3 months
                result["insider_sentiment"].append({
                    "month": entry.get("month", ""),
                    "year": entry.get("year", ""),
                    "change": entry.get("change", 0),
                    "mspr": entry.get("mspr", 0),  # Monthly share purchase ratio
                })

        # Parse social sentiment
        if isinstance(social, dict):
            for platform in ["reddit", "twitter"]:
                entries = social.get(platform, [])
                if isinstance(entries, list):
                    for entry in entries[-7:]:  # Last 7 days
                        result["social_sentiment"][platform].append({
                            "date": entry.get("atTime", ""),
                            "mention": entry.get("mention", 0),
                            "positive_mention": entry.get("positiveMention", 0),
                            "negative_mention": entry.get("negativeMention", 0),
                            "score": entry.get("score", 0),
                        })

        return result

    def get_earnings_surprises(self, ticker: str, limit: int = 4) -> list[dict]:
        """Get recent earnings surprises (actual vs estimate).

        Returns last N quarters of earnings data.
        """
        data = self._get("stock/earnings", {"symbol": ticker, "limit": limit})

        if not isinstance(data, list):
            return []

        surprises = []
        for item in data:
            actual = item.get("actual")
            estimate = item.get("estimate")
            surprise_pct = item.get("surprisePercent", 0)
            surprises.append({
                "period": item.get("period", ""),
                "quarter": item.get("quarter", 0),
                "year": item.get("year", 0),
                "actual_eps": actual,
                "estimate_eps": estimate,
                "surprise_pct": surprise_pct,
                "beat": actual > estimate if actual is not None and estimate is not None else None,
            })
        return surprises

    def get_recommendation_trends(self, ticker: str) -> list[dict]:
        """Get analyst recommendation trends (buy/sell/hold counts)."""
        data = self._get("stock/recommendation", {"symbol": ticker})

        if not isinstance(data, list):
            return []

        trends = []
        for item in data[:4]:  # Last 4 months
            trends.append({
                "period": item.get("period", ""),
                "strong_buy": item.get("strongBuy", 0),
                "buy": item.get("buy", 0),
                "hold": item.get("hold", 0),
                "sell": item.get("sell", 0),
                "strong_sell": item.get("strongSell", 0),
            })
        return trends
