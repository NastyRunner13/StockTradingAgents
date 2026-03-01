"""
NexusTrade — Sentiment Analyst Agent
Analyzes social media sentiment, Reddit, and public mood.
"""

from langchain_core.messages import HumanMessage, SystemMessage
from models.schemas import AnalystReport, Sentiment
from data.stock_provider import StockProvider
from datetime import datetime
import json
import logging
from utils.json_parser import safe_parse_json

logger = logging.getLogger("nexustrade.sentiment")


SENTIMENT_ANALYST_SYSTEM = """You are a senior Sentiment Analyst at a quantitative trading firm.
Your job is to analyze social sentiment, news headlines, and public mood around a given asset.

Given news headlines and market context, you must assess:
- Overall public sentiment (social media buzz, retail investor mood)
- Whether sentiment is diverging from price action (contrarian signals)
- Any unusual hype or fear patterns

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
    stock_provider = StockProvider()

    async def sentiment_analyst_node(state: dict) -> dict:
        ticker = state["ticker"]
        logger.info(f"💭 Sentiment Analyst started for {ticker}")

        # Fetch news as proxy for sentiment
        news = stock_provider.get_news(ticker)
        news_text = "\n".join(
            [f"- {n['title']} ({n['publisher']})" for n in news]
        ) if news else "No recent news available."

        # Get basic price context
        price = stock_provider.get_current_price(ticker)

        import uuid
        run_id = str(uuid.uuid4())[:8]
        now = datetime.now().strftime("%Y-%m-%d %H:%M:%S")

        data_prompt = f"""
Analysis Run: {run_id} | Timestamp: {now}

Analyze the sentiment landscape for {ticker} (current price: ${price or 'N/A'}):

RECENT NEWS & HEADLINES:
{news_text}

Based on these headlines and your understanding of market sentiment patterns, 
provide your sentiment analysis in the required JSON format.
Consider: Is sentiment too euphoric (contrarian sell signal)? Too fearful (contrarian buy signal)?
"""

        messages = [
            SystemMessage(content=SENTIMENT_ANALYST_SYSTEM),
            HumanMessage(content=data_prompt),
        ]

        response = await llm.ainvoke(messages)

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
            analyst_type="sentiment",
            ticker=ticker,
            summary=result.get("summary", ""),
            sentiment=Sentiment(result.get("sentiment", "neutral")),
            confidence=float(result.get("confidence", 0.5)),
            key_findings=result.get("key_findings", []),
            raw_data={"news": news},
            reasoning=result.get("reasoning", ""),
        )

        logger.info(f"💭 Sentiment Analyst done — {report.sentiment.value} (conf: {report.confidence:.0%})")
        return {"sentiment_report": report}

    return sentiment_analyst_node
