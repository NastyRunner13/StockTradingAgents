"""
NexusTrade — Fundamentals Analyst Agent
Evaluates company financials, balance sheet, and valuation metrics.
"""

from langchain_core.messages import HumanMessage, SystemMessage
from models.schemas import AnalystReport, Sentiment
from data.stock_provider import StockProvider
from datetime import datetime
import json
import logging
from utils.json_parser import safe_parse_json
from utils.event_bus import event_bus

logger = logging.getLogger("nexustrade.fundamentals")


FUNDAMENTALS_ANALYST_SYSTEM = """You are a senior Fundamentals Analyst at a hedge fund.
Your job is to evaluate the financial health and intrinsic value of a company 
by analyzing its financial statements, valuation ratios, and business metrics.

Focus on:
- Valuation (P/E, P/B, forward P/E — is it expensive or cheap?)
- Profitability (margins, ROE, earnings growth)
- Balance sheet health (debt levels, current ratio, cash position)
- Cash flow quality (free cash flow, operating cash flow)
- Competitive position (market share, moat)

For CRYPTO assets, focus on:
- Network metrics (if available)
- Market dominance
- Use case and adoption trends

Respond ONLY in valid JSON format:
{
    "summary": "...",
    "sentiment": "bullish",
    "confidence": 0.75,
    "key_findings": ["...", "..."],
    "reasoning": "..."
}
"""


def create_fundamentals_analyst(llm):
    """Factory function that returns the fundamentals analyst node function."""
    stock_provider = StockProvider()

    async def fundamentals_analyst_node(state: dict) -> dict:
        ticker = state["ticker"]
        asset_type = state.get("asset_type", "stock")
        analysis_id = state.get("analysis_id")
        logger.info(f"📑 Fundamentals Analyst started for {ticker} ({asset_type})")
        if analysis_id:
            await event_bus.emit("analysis_log", analysis_id, {
                "agent": "Fundamentals Analyst",
                "stage": "started",
                "message": f"Analyzing financials for {ticker}",
                "details": "",
                "timestamp": datetime.utcnow().isoformat()
            })

        import uuid
        run_id = str(uuid.uuid4())[:8]
        now = datetime.now().strftime("%Y-%m-%d %H:%M:%S")

        if asset_type == "crypto":
            # For crypto, we provide what data we have
            data_prompt = f"""
Analysis Run: {run_id} | Timestamp: {now}

Analyze the fundamentals of {ticker} as a cryptocurrency asset.
Consider its market position, use case, adoption trends, and competitive landscape.
Note: Traditional financial statements are not available for crypto assets.
Provide your analysis in the required JSON format.
"""
        else:
            fundamentals = stock_provider.get_fundamentals(ticker)
            balance_sheet = stock_provider.get_balance_sheet(ticker)
            cashflow = stock_provider.get_cashflow(ticker)
            income_stmt = stock_provider.get_income_statement(ticker)

            data_prompt = f"""
Analysis Run: {run_id} | Timestamp: {now}

Analyze the fundamentals of {ticker}:

VALUATION & KEY METRICS:
{json.dumps(fundamentals, indent=2, default=str)}

BALANCE SHEET (latest):
{json.dumps(dict(list(balance_sheet.items())[:15]), indent=2, default=str)}

CASH FLOW (latest):
{json.dumps(dict(list(cashflow.items())[:10]), indent=2, default=str)}

INCOME STATEMENT (latest):
{json.dumps(dict(list(income_stmt.items())[:10]), indent=2, default=str)}

Assess the company's financial health, valuation attractiveness, and growth prospects.
Provide your analysis in the required JSON format.
"""

        messages = [
            SystemMessage(content=FUNDAMENTALS_ANALYST_SYSTEM),
            HumanMessage(content=data_prompt),
        ]

        if analysis_id:
            await event_bus.emit("analysis_log", analysis_id, {
                "agent": "Fundamentals Analyst",
                "stage": "llm_call",
                "message": "Generating fundamental insights",
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

        raw_data = {}
        if asset_type != "crypto":
            raw_data = stock_provider.get_fundamentals(ticker)

        report = AnalystReport(
            analyst_type="fundamentals",
            ticker=ticker,
            summary=result.get("summary", ""),
            sentiment=Sentiment(result.get("sentiment", "neutral")),
            confidence=float(result.get("confidence", 0.5)),
            key_findings=result.get("key_findings", []),
            raw_data=raw_data,
            reasoning=result.get("reasoning", ""),
        )

        logger.info(f"📑 Fundamentals Analyst done — {report.sentiment.value} (conf: {report.confidence:.0%})")
        if analysis_id:
            await event_bus.emit("analysis_log", analysis_id, {
                "agent": "Fundamentals Analyst",
                "stage": "completed",
                "message": f"Done — Sentiment: {report.sentiment.value}",
                "details": result.get("reasoning", ""),
                "timestamp": datetime.utcnow().isoformat()
            })
        return {"fundamentals_report": report}

    return fundamentals_analyst_node
