"""
NexusTrade — News Analyst Agent
Monitors global news, macroeconomic events, and insider activity.
"""

from langchain_core.messages import HumanMessage, SystemMessage
from models.schemas import AnalystReport, Sentiment
from data.stock_provider import StockProvider
from datetime import datetime
import json
import logging
from utils.json_parser import safe_parse_json
from utils.event_bus import event_bus

logger = logging.getLogger("nexustrade.news")


NEWS_ANALYST_SYSTEM = """You are a senior News & Macro Analyst at a global trading firm.
Your job is to analyze recent news, geopolitical events, macroeconomic indicators, 
and insider transactions to assess their impact on a given asset.

Focus on:
- Material news that could move the stock price
- Macro trends (interest rates, inflation, sector rotation)
- Insider buying/selling patterns (smart money signals)
- Regulatory or geopolitical risks

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
    stock_provider = StockProvider()

    async def news_analyst_node(state: dict) -> dict:
        ticker = state["ticker"]
        analysis_id = state.get("analysis_id")
        logger.info(f"📰 News Analyst started for {ticker}")
        if analysis_id:
            await event_bus.emit("analysis_log", analysis_id, {
                "agent": "News Analyst",
                "stage": "started",
                "message": f"Hunting latest news for {ticker}",
                "details": "",
                "timestamp": datetime.utcnow().isoformat()
            })

        # Fetch news and insider data
        news = stock_provider.get_news(ticker)
        insiders = stock_provider.get_insider_transactions(ticker)

        news_text = "\n".join(
            [f"- {n['title']} ({n['publisher']})" for n in news]
        ) if news else "No recent news available."

        insider_text = ""
        if insiders:
            insider_text = "\nINSIDER TRANSACTIONS:\n"
            for tx in insiders[:5]:
                insider_text += f"- {tx}\n"

        import uuid
        run_id = str(uuid.uuid4())[:8]
        now = datetime.now().strftime("%Y-%m-%d %H:%M:%S")

        data_prompt = f"""
Analysis Run: {run_id} | Timestamp: {now}

Analyze the news landscape and insider activity for {ticker}:

RECENT NEWS:
{news_text}
{insider_text}

Assess the potential impact of these developments on the stock. 
Consider both immediate catalysts and longer-term implications.
Provide your analysis in the required JSON format.
"""

        messages = [
            SystemMessage(content=NEWS_ANALYST_SYSTEM),
            HumanMessage(content=data_prompt),
        ]

        if analysis_id:
            await event_bus.emit("analysis_log", analysis_id, {
                "agent": "News Analyst",
                "stage": "llm_call",
                "message": "Generating news insights",
                "details": "",
                "timestamp": datetime.utcnow().isoformat()
            })

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
            analyst_type="news",
            ticker=ticker,
            summary=result.get("summary", ""),
            sentiment=Sentiment(result.get("sentiment", "neutral")),
            confidence=float(result.get("confidence", 0.5)),
            key_findings=result.get("key_findings", []),
            raw_data={"news": news, "insiders": insiders},
            reasoning=result.get("reasoning", ""),
        )

        logger.info(f"📰 News Analyst done — {report.sentiment.value} (conf: {report.confidence:.0%})")
        if analysis_id:
            await event_bus.emit("analysis_log", analysis_id, {
                "agent": "News Analyst",
                "stage": "completed",
                "message": f"Done — Sentiment: {report.sentiment.value}",
                "details": result.get("reasoning", ""),
                "timestamp": datetime.utcnow().isoformat()
            })
        return {"news_report": report}

    return news_analyst_node
