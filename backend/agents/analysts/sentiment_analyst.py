"""
NexusTrade — Sentiment Analyst Agent
Analyzes social media sentiment, news tone, and public mood.
Enhanced with Finnhub social sentiment scores (Reddit/Twitter buzz).
"""

from langchain_core.messages import HumanMessage, SystemMessage
from models.schemas import AnalystReport, Sentiment
from data.news_aggregator import NewsAggregator
from data.stock_provider import StockProvider
from datetime import datetime
import logging
from utils.json_parser import safe_parse_json

logger = logging.getLogger("nexustrade.sentiment")


SENTIMENT_ANALYST_SYSTEM = """You are a senior Sentiment Analyst at a quantitative trading firm.
Your job is to analyze social sentiment, news tone, public mood, and social media buzz around a given asset.

You have TWO types of sentiment data available:
1. NEWS-BASED SENTIMENT: Headlines and their tone (bullish/bearish/neutral)
2. SOCIAL MEDIA SENTIMENT: Reddit and Twitter mention volumes — positive vs negative

Your analysis should cover:
- Overall public sentiment (retail vs institutional mood)
- Social media buzz trends (increasing/decreasing mentions, sentiment ratio)
- Whether sentiment is diverging from price action (contrarian signals)
- Unusual hype or fear patterns (FOMO, panic selling indicators)
- Sentiment momentum (is sentiment improving or deteriorating?)

Respond ONLY in valid JSON format:
{
    "summary": "...",
    "sentiment": "bullish",
    "confidence": 0.75,
    "key_findings": ["...", "..."],
    "reasoning": "..."
}
"""


def create_sentiment_analyst(llm):
    """Factory function that returns the sentiment analyst node function."""
    aggregator = NewsAggregator()
    stock_provider = StockProvider()

    async def sentiment_analyst_node(state: dict, config: dict = None) -> dict:
        ticker = state["ticker"]
        log_callback = (config or {}).get("configurable", {}).get("_log_callback")
        logger.info(f"💭 Sentiment Analyst started for {ticker}")

        async def _log(stage: str, message: str, details: str = ""):
            logger.info(f"💭 [Sentiment] {stage}: {message}")
            if details:
                logger.info(f"   ↳ {details[:300]}")
            if log_callback:
                await log_callback("Sentiment Analyst", stage, message, details)

        await _log("started", f"Fetching sentiment data for {ticker}")

        # Fetch unified news bundle (includes social sentiment)
        bundle = aggregator.get_full_news_bundle(ticker)

        # Get basic price context
        price = stock_provider.get_current_price(ticker)

        # Format news headlines with sentiment
        headlines = bundle.articles[:15]
        news_text = "\n".join([
            f"- {h['title']} ({h.get('publisher', '?')}) — {h.get('overall_sentiment', 'N/A')}"
            for h in headlines
        ]) if headlines else "No recent headlines available."

        # Format social media sentiment data
        social_text = ""
        social = bundle.social_sentiment
        if social:
            for platform in ["reddit", "twitter"]:
                entries = social.get("social_sentiment", {}).get(platform, [])
                if entries:
                    total = sum(e.get("mention", 0) for e in entries)
                    positive = sum(e.get("positive_mention", 0) for e in entries)
                    negative = sum(e.get("negative_mention", 0) for e in entries)
                    avg_score = sum(e.get("score", 0) for e in entries) / len(entries) if entries else 0

                    # Trend: compare last 3 days vs first 3 days
                    if len(entries) >= 6:
                        recent = sum(e.get("mention", 0) for e in entries[-3:])
                        earlier = sum(e.get("mention", 0) for e in entries[:3])
                        trend = "📈 INCREASING" if recent > earlier * 1.2 else "📉 DECREASING" if recent < earlier * 0.8 else "→ STABLE"
                    else:
                        trend = "N/A"

                    social_text += f"""
{platform.upper()} SENTIMENT (7-day):
  Total mentions: {total}
  Positive: {positive} | Negative: {negative}
  Sentiment ratio: {positive / max(total, 1):.0%} positive
  Avg sentiment score: {avg_score:.2f}
  Trend: {trend}
"""

        # Format insider sentiment from Finnhub
        insider_sentiment_text = ""
        insider_data = social.get("insider_sentiment", []) if social else []
        if insider_data:
            insider_sentiment_text = "\nINSIDER SENTIMENT (Monthly Share Purchase Ratio):\n"
            for entry in insider_data:
                mspr = entry.get("mspr", 0)
                signal = "🟢 NET BUYING" if mspr > 0 else "🔴 NET SELLING" if mspr < 0 else "⚪ NEUTRAL"
                insider_sentiment_text += f"  {entry.get('year', '')}-{entry.get('month', '')}: MSPR={mspr:.2f} ({signal})\n"

        # Log fetched data
        headline_count = len(headlines)
        has_social = bool(social_text.strip())
        await _log(
            "data_fetched",
            f"{headline_count} headlines, Social data: {'Yes' if has_social else 'No'}, Price: ${price or 'N/A'}",
            f"Top: {headlines[0]['title'][:80]}" if headlines else "None",
        )

        import uuid
        run_id = str(uuid.uuid4())[:8]
        now = datetime.now().strftime("%Y-%m-%d %H:%M:%S")

        data_prompt = f"""
Analysis Run: {run_id} | Timestamp: {now}

Analyze the sentiment landscape for {ticker} (current price: ${price or 'N/A'}):

─── NEWS SENTIMENT ───
{news_text}

─── SOCIAL MEDIA SENTIMENT ───
{social_text if social_text.strip() else "No social media data available."}

{insider_sentiment_text}

Based on these data points, provide your sentiment analysis.
Consider:
- Is sentiment too euphoric (contrarian sell signal)? Too fearful (contrarian buy signal)?
- Is social media buzz increasing or fading?
- Are insiders buying or selling?
- Does the sentiment align with or diverge from recent price action?
"""

        messages = [
            SystemMessage(content=SENTIMENT_ANALYST_SYSTEM),
            HumanMessage(content=data_prompt),
        ]

        await _log("llm_call", "Sending enriched prompt to LLM for sentiment analysis")
        response = await llm.ainvoke(messages)
        await _log("llm_response", f"Received LLM response ({len(response.content)} chars)", response.content[:300])

        result = safe_parse_json(response.content)
        if "raw_response" in result:
            raw = result["raw_response"]
            result = {
                "summary": raw[:200],
                "sentiment": "neutral",
                "confidence": 0.5,
                "key_findings": [],
                "reasoning": raw,
            }

        # Build enriched raw_data for frontend tabs
        raw_data = {
            "current_price": price,
            "headlines": headlines,
            "source_counts": bundle.source_counts,
        }
        if social:
            raw_data["social_sentiment"] = social.get("social_sentiment", {})
            raw_data["insider_sentiment"] = social.get("insider_sentiment", [])

        report = AnalystReport(
            analyst_type="sentiment",
            ticker=ticker,
            summary=result.get("summary", ""),
            sentiment=Sentiment(result.get("sentiment", "neutral")),
            confidence=float(result.get("confidence", 0.5)),
            key_findings=result.get("key_findings", []),
            raw_data=raw_data,
            reasoning=result.get("reasoning", ""),
        )

        await _log("completed", f"Verdict: {report.sentiment.value} ({report.confidence:.0%} confidence)", report.summary)
        return {"sentiment_report": report}

    return sentiment_analyst_node
