"""
NexusTrade — Market/Technical Analyst Agent
Analyzes price action, technical indicators, and chart patterns.
"""

from langchain_core.messages import HumanMessage, SystemMessage
from models.schemas import AnalystReport, Sentiment, AssetType
from data.stock_provider import StockProvider
from data.crypto_provider import CryptoProvider
from datetime import datetime
import json
import logging
from utils.json_parser import safe_parse_json
from utils.event_bus import event_bus

logger = logging.getLogger("nexustrade.market")


MARKET_ANALYST_SYSTEM = """You are a senior Market & Technical Analyst at a top-tier trading firm. 
Your job is to analyze price action, technical indicators, and chart patterns to assess the current 
market position of the given asset.

You must provide:
1. A clear SUMMARY of the current technical picture (2-3 sentences)
2. Your SENTIMENT (very_bullish, bullish, neutral, bearish, very_bearish)
3. Your CONFIDENCE (0.0 to 1.0)
4. KEY FINDINGS (list of 3-5 bullet points)
5. Your detailed REASONING

Respond ONLY in valid JSON format:
{
    "summary": "...",
    "sentiment": "bullish",
    "confidence": 0.75,
    "key_findings": ["...", "..."],
    "reasoning": "..."
}
"""


def create_market_analyst(llm):
    """Factory function that returns the market analyst node function."""
    stock_provider = StockProvider()
    crypto_provider = CryptoProvider()

    async def market_analyst_node(state: dict) -> dict:
        ticker = state["ticker"]
        asset_type = state.get("asset_type", "stock")
        analysis_id = state.get("analysis_id")
        
        logger.info(f"📊 Market Analyst started for {ticker} ({asset_type})")
        if analysis_id:
            await event_bus.emit("analysis_log", analysis_id, {
                "agent": "Market Analyst",
                "stage": "started",
                "message": f"Analyzing technicals for {ticker}",
                "details": "",
                "timestamp": datetime.utcnow().isoformat()
            })

        # Fetch technical data
        if asset_type == "crypto":
            indicators = crypto_provider.get_technical_indicators(ticker)
            price_data = crypto_provider.get_price_data(ticker, limit=30)
            price_summary = f"Last 30 days data available. Latest close: {indicators.get('current_price', 'N/A')}"
        else:
            indicators = stock_provider.get_technical_indicators(ticker)
            price_data = stock_provider.get_price_data(ticker, period="3mo")
            price_summary = f"3-month data available. Latest close: {indicators.get('current_price', 'N/A')}"

        import uuid
        run_id = str(uuid.uuid4())[:8]
        now = datetime.now().strftime("%Y-%m-%d %H:%M:%S")

        data_prompt = f"""
Analysis Run: {run_id} | Timestamp: {now}

Analyze the following technical data for {ticker}:

TECHNICAL INDICATORS:
{json.dumps(indicators, indent=2, default=str)}

PRICE CONTEXT:
{price_summary}

Provide your technical analysis in the required JSON format.
"""

        messages = [
            SystemMessage(content=MARKET_ANALYST_SYSTEM),
            HumanMessage(content=data_prompt),
        ]

        if analysis_id:
            await event_bus.emit("analysis_log", analysis_id, {
                "agent": "Market Analyst",
                "stage": "llm_call",
                "message": "Generating technical insights",
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
                "key_findings": ["Unable to parse structured response"],
                "reasoning": raw,
            }

        report = AnalystReport(
            analyst_type="market",
            ticker=ticker,
            summary=result.get("summary", ""),
            sentiment=Sentiment(result.get("sentiment", "neutral")),
            confidence=float(result.get("confidence", 0.5)),
            key_findings=result.get("key_findings", []),
            raw_data=indicators,
            reasoning=result.get("reasoning", ""),
        )

        logger.info(f"📊 Market Analyst done — {report.sentiment.value} (conf: {report.confidence:.0%})")
        if analysis_id:
            await event_bus.emit("analysis_log", analysis_id, {
                "agent": "Market Analyst",
                "stage": "completed",
                "message": f"Done — Sentiment: {report.sentiment.value}",
                "details": result.get("reasoning", ""),
                "timestamp": datetime.utcnow().isoformat()
            })
        return {"market_report": report}

    return market_analyst_node
