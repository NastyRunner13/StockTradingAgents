"""
NexusTrade — Trader Agent
Synthesizes research thesis into a concrete trade plan.
"""

from langchain_core.messages import HumanMessage, SystemMessage
from models.schemas import TradeSignal, TradeAction, AssetType
from datetime import datetime
import json
import logging
from utils.json_parser import safe_parse_json

logger = logging.getLogger("nexustrade.trader")


TRADER_SYSTEM = """You are a senior Trader at an algorithmic trading firm.
You receive an investment thesis from the research team and must create a concrete trade plan.

Your trade plan must include:
- ACTION: buy, sell, hold, short, or cover
- CONFIDENCE: 0.0 to 1.0 (how confident you are in this trade)
- ENTRY STRATEGY: target entry price
- EXIT STRATEGY: target price (profit target) and stop-loss
- POSITION SIZE: suggested portfolio allocation (scale with conviction: 2-5% low, 5-15% medium, 15-30% high)
- REASONING: why this specific trade setup makes sense

IMPORTANT: Position size should vary based on your confidence and the risk/reward ratio.
Do NOT default to a fixed size. Think about what % of portfolio this specific trade deserves.

Respond ONLY in valid JSON:
{
    "action": "buy",
    "confidence": 0.75,
    "entry_price": 150.00,
    "target_price": 170.00,
    "stop_loss": 140.00,
    "position_size_pct": <choose 0.02 to 0.30 based on conviction>,
    "reasoning": "..."
}
"""


def create_trader(llm, memory=None):
    """Factory for trader node."""

    async def trader_node(state: dict) -> dict:
        ticker = state["ticker"]
        asset_type = state.get("asset_type", "stock")
        logger.info(f"💰 Trader started for {ticker}")
        debate = state.get("investment_debate", {})
        
        if hasattr(debate, "model_dump"):
            debate_data = debate.model_dump()
        elif isinstance(debate, dict):
            debate_data = debate
        else:
            debate_data = {}

        thesis = debate_data.get("investment_thesis", "No thesis available")
        verdict = debate_data.get("judge_verdict", "neutral")
        judge_confidence = debate_data.get("judge_confidence", 0.5)

        # Get current price context
        market_report = state.get("market_report")
        current_price = None
        if market_report:
            rd = market_report if isinstance(market_report, dict) else market_report.model_dump()
            current_price = rd.get("raw_data", {}).get("current_price")

        memory_context = ""
        if memory:
            memories = memory.get_memories(f"{ticker} {verdict} trading", n_matches=2)
            if memories:
                memory_context = "\nPAST TRADES IN SIMILAR SITUATIONS:\n"
                for m in memories:
                    memory_context += f"- {m['recommendation'][:150]}\n"

        prompt = f"""
TICKER: {ticker}
ASSET TYPE: {asset_type}
CURRENT PRICE: ${current_price or 'Unknown'}

RESEARCH VERDICT: {verdict} (confidence: {judge_confidence})
INVESTMENT THESIS: {thesis}
{memory_context}

Create your trade plan.
"""
        messages = [SystemMessage(content=TRADER_SYSTEM), HumanMessage(content=prompt)]
        response = await llm.ainvoke(messages)

        result = safe_parse_json(response.content)
        if "raw_response" in result:
            result = {"action": "hold", "confidence": 0.5, "reasoning": result["raw_response"]}

        trade_signal = TradeSignal(
            ticker=ticker,
            asset_type=AssetType(asset_type),
            action=TradeAction(result.get("action", "hold")),
            confidence=float(result.get("confidence", 0.5)),
            entry_price=result.get("entry_price"),
            target_price=result.get("target_price"),
            stop_loss=result.get("stop_loss"),
            position_size_pct=min(float(result.get("position_size_pct", 0.05)), 0.3),
            reasoning=result.get("reasoning", ""),
        )

        logger.info(f"💰 Trader done — {trade_signal.action.value} (conf: {trade_signal.confidence:.0%}, size: {trade_signal.position_size_pct:.0%})")
        return {"trade_signal": trade_signal}

    return trader_node
