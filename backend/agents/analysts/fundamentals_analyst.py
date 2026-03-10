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

    async def fundamentals_analyst_node(state: dict, config: dict = None) -> dict:
        ticker = state["ticker"]
        asset_type = state.get("asset_type", "stock")
        log_callback = (config or {}).get("configurable", {}).get("_log_callback")
        logger.info(f"📑 Fundamentals Analyst started for {ticker} ({asset_type})")

        async def _log(stage: str, message: str, details: str = ""):
            logger.info(f"📑 [Fundamentals] {stage}: {message}")
            if details:
                logger.info(f"   ↳ {details[:300]}")
            if log_callback:
                await log_callback("Fundamentals Analyst", stage, message, details)

        await _log("started", f"Fetching financial data for {ticker}")

        import uuid
        run_id = str(uuid.uuid4())[:8]
        now = datetime.now().strftime("%Y-%m-%d %H:%M:%S")

        if asset_type == "crypto":
            await _log("data_fetched", "Crypto asset — no traditional financials", "Using market position and adoption analysis")
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

            # Log key metrics
            pe = fundamentals.get("pe_ratio", "N/A")
            mcap = fundamentals.get("market_cap", "N/A")
            if isinstance(mcap, (int, float)) and mcap:
                mcap = f"${mcap/1e9:.1f}B" if mcap > 1e9 else f"${mcap/1e6:.0f}M"
            roe = fundamentals.get("roe", "N/A")
            if isinstance(roe, float):
                roe = f"{roe*100:.1f}%"
            await _log("data_fetched", f"P/E: {pe}, Mkt Cap: {mcap}, ROE: {roe}", json.dumps(fundamentals, default=str)[:500])

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

        await _log("llm_call", "Sending prompt to LLM for fundamentals analysis")
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

        raw_data = {}
        if asset_type != "crypto":
            raw_data = fundamentals

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

        await _log("completed", f"Verdict: {report.sentiment.value} ({report.confidence:.0%} confidence)", report.summary)
        return {"fundamentals_report": report}

    return fundamentals_analyst_node
