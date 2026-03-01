"""
NexusTrade — Risk Debate Agents (Aggressive, Conservative, Neutral)
Three risk analysts debate the proposed trade to determine appropriate risk management.
"""

from langchain_core.messages import HumanMessage, SystemMessage
from models.schemas import DebateMessage, RiskDebateState
import json
import logging
from utils.json_parser import safe_parse_json

logger = logging.getLogger("nexustrade.risk")


AGGRESSIVE_SYSTEM = """You are an AGGRESSIVE Risk Analyst. You believe in taking calculated risks 
for higher returns. You tend to favor larger position sizes and tighter stop-losses to maximize 
reward-to-risk ratios. Argue for a more aggressive approach.

Respond in valid JSON:
{
    "argument": "Your risk assessment and recommendation (1-2 paragraphs)",
    "recommended_position_pct": 0.15,
    "recommended_stop_loss_pct": 0.03,
    "risk_rating": "acceptable"
}
"""

CONSERVATIVE_SYSTEM = """You are a CONSERVATIVE Risk Analyst. You prioritize capital preservation 
above all else. You favor smaller positions, wider stop-losses, and often recommend reducing 
exposure. Argue for a more cautious approach.

Respond in valid JSON:
{
    "argument": "Your risk assessment and recommendation (1-2 paragraphs)",
    "recommended_position_pct": 0.05,
    "recommended_stop_loss_pct": 0.08,
    "risk_rating": "high_risk"
}
"""

NEUTRAL_SYSTEM = """You are a NEUTRAL Risk Analyst. You balance risk and reward objectively.
You consider both the aggressive and conservative viewpoints and aim for optimal risk-adjusted returns.

Respond in valid JSON:
{
    "argument": "Your balanced risk assessment (1-2 paragraphs)",
    "recommended_position_pct": 0.10,
    "recommended_stop_loss_pct": 0.05,
    "risk_rating": "moderate"
}
"""

RISK_JUDGE_SYSTEM = """You are the Chief Risk Officer. You've reviewed the risk debate between 
aggressive, conservative, and neutral risk analysts about a proposed trade.

Deliver your final risk assessment:
1. Approve or reject the trade
2. Set the final position size
3. Set risk parameters (stop-loss, max loss per trade)

Respond in valid JSON:
{
    "approved": true,
    "verdict": "Approved with modifications",
    "final_position_pct": 0.08,
    "final_stop_loss_pct": 0.05,
    "max_portfolio_risk_pct": 0.02,
    "reasoning": "Detailed explanation of the risk decision"
}
"""


def _format_trade_context(state: dict) -> str:
    """Format trade signal for risk analysts."""
    signal = state.get("trade_signal")
    if signal:
        s = signal if isinstance(signal, dict) else signal.model_dump()
        return f"""
PROPOSED TRADE:
- Ticker: {s.get('ticker')}
- Action: {s.get('action')}
- Confidence: {s.get('confidence')}
- Entry: ${s.get('entry_price', 'N/A')}
- Target: ${s.get('target_price', 'N/A')}
- Stop Loss: ${s.get('stop_loss', 'N/A')}
- Proposed Size: {s.get('position_size_pct', 0) * 100:.1f}%
- Reasoning: {s.get('reasoning', 'N/A')[:300]}
"""
    return "No trade signal available."


def create_aggressive_debater(llm):
    async def node(state: dict) -> dict:
        logger.info("🟢 Aggressive Risk Analyst started")
        context = _format_trade_context(state)
        debate = state.get("risk_debate") or RiskDebateState()
        if isinstance(debate, dict):
            debate = RiskDebateState(**debate)

        previous = ""
        if debate.conservative_arguments:
            previous += f"\nConservative's view: {debate.conservative_arguments[-1].content}"

        prompt = f"{context}\n{previous}\n\nProvide your AGGRESSIVE risk assessment."
        messages = [SystemMessage(content=AGGRESSIVE_SYSTEM), HumanMessage(content=prompt)]
        response = await llm.ainvoke(messages)

        result = safe_parse_json(response.content)
        if "raw_response" in result:
            result = {"argument": result["raw_response"]}

        msg = DebateMessage(speaker="aggressive", content=result.get("argument", response.content))
        debate.aggressive_arguments.append(msg)
        debate.round_count = len(debate.aggressive_arguments)

        logger.info(f"🟢 Aggressive done — {result.get('risk_rating', 'N/A')}")
        return {"risk_debate": debate}

    return node


def create_conservative_debater(llm):
    async def node(state: dict) -> dict:
        logger.info("🟡 Conservative Risk Analyst started")
        context = _format_trade_context(state)
        debate = state.get("risk_debate") or RiskDebateState()
        if isinstance(debate, dict):
            debate = RiskDebateState(**debate)

        previous = ""
        if debate.aggressive_arguments:
            previous += f"\nAggressive's view: {debate.aggressive_arguments[-1].content}"

        prompt = f"{context}\n{previous}\n\nProvide your CONSERVATIVE risk assessment."
        messages = [SystemMessage(content=CONSERVATIVE_SYSTEM), HumanMessage(content=prompt)]
        response = await llm.ainvoke(messages)

        result = safe_parse_json(response.content)
        if "raw_response" in result:
            result = {"argument": result["raw_response"]}

        msg = DebateMessage(speaker="conservative", content=result.get("argument", response.content))
        debate.conservative_arguments.append(msg)

        logger.info(f"🟡 Conservative done — {result.get('risk_rating', 'N/A')}")
        return {"risk_debate": debate}

    return node


def create_neutral_debater(llm):
    async def node(state: dict) -> dict:
        logger.info("⚪ Neutral Risk Analyst started")
        context = _format_trade_context(state)
        debate = state.get("risk_debate") or RiskDebateState()
        if isinstance(debate, dict):
            debate = RiskDebateState(**debate)

        previous = ""
        if debate.aggressive_arguments:
            previous += f"\nAggressive's view: {debate.aggressive_arguments[-1].content}"
        if debate.conservative_arguments:
            previous += f"\nConservative's view: {debate.conservative_arguments[-1].content}"

        prompt = f"{context}\n{previous}\n\nProvide your NEUTRAL balanced risk assessment."
        messages = [SystemMessage(content=NEUTRAL_SYSTEM), HumanMessage(content=prompt)]
        response = await llm.ainvoke(messages)

        result = safe_parse_json(response.content)
        if "raw_response" in result:
            result = {"argument": result["raw_response"]}

        msg = DebateMessage(speaker="neutral", content=result.get("argument", response.content))
        debate.neutral_arguments.append(msg)

        logger.info(f"⚪ Neutral done — {result.get('risk_rating', 'N/A')}")
        return {"risk_debate": debate}

    return node


def create_risk_judge(llm, memory=None):
    async def node(state: dict) -> dict:
        logger.info("🛡️ Risk Judge deliberating...")
        context = _format_trade_context(state)
        debate = state.get("risk_debate") or RiskDebateState()
        if isinstance(debate, dict):
            debate = RiskDebateState(**debate)

        debate_transcript = ""
        max_rounds = max(
            len(debate.aggressive_arguments),
            len(debate.conservative_arguments),
            len(debate.neutral_arguments),
        )
        for i in range(max_rounds):
            debate_transcript += f"\n--- ROUND {i+1} ---"
            if i < len(debate.aggressive_arguments):
                debate_transcript += f"\nAGGRESSIVE: {debate.aggressive_arguments[i].content}"
            if i < len(debate.conservative_arguments):
                debate_transcript += f"\nCONSERVATIVE: {debate.conservative_arguments[i].content}"
            if i < len(debate.neutral_arguments):
                debate_transcript += f"\nNEUTRAL: {debate.neutral_arguments[i].content}"

        prompt = f"""
{context}

RISK DEBATE TRANSCRIPT:
{debate_transcript}

Deliver your final risk judgment.
"""
        messages = [SystemMessage(content=RISK_JUDGE_SYSTEM), HumanMessage(content=prompt)]
        response = await llm.ainvoke(messages)

        result = safe_parse_json(response.content)
        if "raw_response" in result:
            result = {"approved": False, "verdict": result["raw_response"]}

        debate.judge_verdict = result.get("verdict", "")
        debate.recommended_position_size = float(result.get("final_position_pct", 0.05))

        # Update trade signal with risk-adjusted parameters
        trade_signal = state.get("trade_signal")
        if trade_signal:
            if hasattr(trade_signal, "model_copy"):
                trade_signal = trade_signal.model_copy(update={
                    "position_size_pct": debate.recommended_position_size,
                })
            elif isinstance(trade_signal, dict):
                trade_signal["position_size_pct"] = debate.recommended_position_size

        final_decision = f"""
TRADE {'APPROVED' if result.get('approved', False) else 'REJECTED'}
Ticker: {state.get('ticker')}
Action: {trade_signal.action if hasattr(trade_signal, 'action') else trade_signal.get('action', 'hold')}
Position Size: {debate.recommended_position_size * 100:.1f}%
Max Risk: {result.get('max_portfolio_risk_pct', 0.02) * 100:.1f}%
Reasoning: {result.get('reasoning', '')}
"""

        approved = result.get('approved', False)
        logger.info(f"🛡️ Risk Judge verdict: {'APPROVED' if approved else 'REJECTED'} — pos size: {debate.recommended_position_size:.0%}")

        return {
            "risk_debate": debate,
            "trade_signal": trade_signal,
            "final_decision": final_decision,
            "trade_approved": result.get("approved", False),
        }

    return node
