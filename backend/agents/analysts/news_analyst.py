"""
NexusTrade — News Analyst Agent
Monitors global news, macroeconomic events, earnings, and insider activity.
Uses NewsAggregator for comprehensive multi-source coverage.
"""

from langchain_core.messages import HumanMessage, SystemMessage
from models.schemas import AnalystReport, Sentiment
from data.news_aggregator import NewsAggregator
from datetime import datetime
import logging
from utils.json_parser import safe_parse_json

logger = logging.getLogger("nexustrade.news")


NEWS_ANALYST_SYSTEM = """You are a senior News & Macro Analyst at a global trading firm.
Your job is to analyze recent news, geopolitical events, macroeconomic indicators,
earnings data, analyst recommendations, and insider transactions to assess their impact on a given asset.

Focus on:
- Material news that could move the stock price (catalysts, partnerships, lawsuits, M&A)
- Macro trends (interest rates, inflation, sector rotation, geopolitical risks)
- Earnings performance (beat/miss vs estimates, forward guidance)
- Analyst consensus (buy/sell/hold distribution and changes)
- Insider buying/selling patterns (smart money signals)

Respond ONLY in valid JSON format:
{
    "summary": "...",
    "sentiment": "bullish",
    "confidence": 0.75,
    "key_findings": ["...", "..."],
    "reasoning": "..."
}
"""


def create_news_analyst(llm):
    """Factory function that returns the news analyst node function."""
    aggregator = NewsAggregator()

    async def news_analyst_node(state: dict, config: dict = None) -> dict:
        ticker = state["ticker"]
        log_callback = (config or {}).get("configurable", {}).get("_log_callback")
        logger.info(f"📰 News Analyst started for {ticker}")

        async def _log(stage: str, message: str, details: str = ""):
            logger.info(f"📰 [News] {stage}: {message}")
            if details:
                logger.info(f"   ↳ {details[:300]}")
            if log_callback:
                await log_callback("News Analyst", stage, message, details)

        await _log("started", f"Fetching comprehensive news data for {ticker}")

        # Fetch unified news bundle from all sources
        bundle = aggregator.get_full_news_bundle(ticker)

        # Format articles for LLM
        if bundle.articles:
            news_text = "\n".join([
                f"- [{a.get('source_provider', '?')}] {a['title']} ({a.get('publisher', 'Unknown')}) "
                f"— Sentiment: {a.get('overall_sentiment', 'N/A')}"
                for a in bundle.articles[:20]
            ])
        else:
            news_text = "No recent news available."

        # Format earnings data
        earnings_text = ""
        if bundle.earnings_surprises:
            earnings_text = "\nEARNINGS HISTORY:\n"
            for e in bundle.earnings_surprises:
                beat = "✅ BEAT" if e.get("beat") else "❌ MISS" if e.get("beat") is False else "N/A"
                earnings_text += (
                    f"- {e.get('period', '?')}: EPS ${e.get('actual_eps', '?')} vs "
                    f"${e.get('estimate_eps', '?')} ({beat}, {e.get('surprise_pct', 0):+.1f}%)\n"
                )

        # Format recommendation trends
        rec_text = ""
        if bundle.recommendation_trends:
            latest = bundle.recommendation_trends[0]
            rec_text = (
                f"\nANALYST CONSENSUS ({latest.get('period', '')}):\n"
                f"- Strong Buy: {latest.get('strong_buy', 0)} | Buy: {latest.get('buy', 0)} | "
                f"Hold: {latest.get('hold', 0)} | Sell: {latest.get('sell', 0)} | "
                f"Strong Sell: {latest.get('strong_sell', 0)}\n"
            )

        # Format social sentiment
        social_text = ""
        social = bundle.social_sentiment
        if social:
            for platform in ["reddit", "twitter"]:
                entries = social.get("social_sentiment", {}).get(platform, [])
                if entries:
                    total_mentions = sum(e.get("mention", 0) for e in entries)
                    total_positive = sum(e.get("positive_mention", 0) for e in entries)
                    total_negative = sum(e.get("negative_mention", 0) for e in entries)
                    if total_mentions > 0:
                        social_text += (
                            f"\n{platform.upper()} BUZZ (7d): {total_mentions} mentions "
                            f"(+{total_positive} positive, -{total_negative} negative)\n"
                        )

        # Format insider data
        insider_text = ""
        if bundle.insider_transactions:
            insider_text = "\nINSIDER TRANSACTIONS:\n"
            for tx in bundle.insider_transactions[:5]:
                insider_text += f"- {tx}\n"

        # Log fetched data summary
        await _log(
            "data_fetched",
            f"{len(bundle.articles)} articles from {bundle.source_counts.get('alpha_vantage', 0)} AV + "
            f"{bundle.source_counts.get('finnhub', 0)} FH, "
            f"{len(bundle.earnings_surprises)} earnings quarters",
            f"Top: {bundle.articles[0]['title'][:80]}" if bundle.articles else "No articles",
        )

        import uuid
        run_id = str(uuid.uuid4())[:8]
        now = datetime.now().strftime("%Y-%m-%d %H:%M:%S")

        data_prompt = f"""
Analysis Run: {run_id} | Timestamp: {now}

Analyze the complete news landscape for {ticker}:

RECENT NEWS ({len(bundle.articles)} articles from multiple sources):
{news_text}
{earnings_text}
{rec_text}
{social_text}
{insider_text}

Assess the potential impact of these developments on the stock.
Consider both immediate catalysts and longer-term implications.
Weight earnings performance and analyst consensus heavily.
Provide your analysis in the required JSON format.
"""

        messages = [
            SystemMessage(content=NEWS_ANALYST_SYSTEM),
            HumanMessage(content=data_prompt),
        ]

        await _log("llm_call", "Sending enriched prompt to LLM for news analysis")
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

        report = AnalystReport(
            analyst_type="news",
            ticker=ticker,
            summary=result.get("summary", ""),
            sentiment=Sentiment(result.get("sentiment", "neutral")),
            confidence=float(result.get("confidence", 0.5)),
            key_findings=result.get("key_findings", []),
            raw_data={
                "news": bundle.articles,
                "insiders": bundle.insider_transactions,
                "earnings": bundle.earnings_surprises,
                "recommendations": bundle.recommendation_trends,
                "source_counts": bundle.source_counts,
            },
            reasoning=result.get("reasoning", ""),
        )

        await _log("completed", f"Verdict: {report.sentiment.value} ({report.confidence:.0%} confidence)", report.summary)
        return {"news_report": report}

    return news_analyst_node
