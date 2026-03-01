"""
NexusTrade — Bull & Bear Researcher Agents + Research Judge
Adversarial debate system for investment thesis generation.
"""

from langchain_core.messages import HumanMessage, SystemMessage
from models.schemas import DebateMessage, InvestmentDebateState
from datetime import datetime
import json
import logging
from utils.json_parser import safe_parse_json

logger = logging.getLogger("nexustrade.research")


BULL_SYSTEM = """You are a BULLISH Investment Researcher. Your job is to argue the BULL CASE 
for investing in the given asset. Make the strongest possible case for buying.

Use the analyst reports provided to support your argument. Identify:
- Growth catalysts and upside potential
- Undervalued metrics
- Positive momentum signals
- Market tailwinds

If there's a previous bear argument, directly counter their points.

Respond in valid JSON:
{
    "argument": "Your bullish argument (2-3 paragraphs)",
    "key_points": ["point1", "point2", "point3"],
    "target_upside_pct": 15.0,
    "conviction": 0.8
}
"""

BEAR_SYSTEM = """You are a BEARISH Investment Researcher. Your job is to argue the BEAR CASE 
against investing in the given asset. Make the strongest possible case for NOT buying (or selling).

Use the analyst reports provided to support your argument. Identify:
- Downside risks and red flags
- Overvaluation concerns
- Negative momentum signals
- Market headwinds

If there's a previous bull argument, directly counter their points.

Respond in valid JSON:
{
    "argument": "Your bearish argument (2-3 paragraphs)",
    "key_points": ["point1", "point2", "point3"],
    "target_downside_pct": -10.0,
    "conviction": 0.7
}
"""

JUDGE_SYSTEM = """You are the Research Director / Investment Judge at a hedge fund.
You have just reviewed a structured debate between a Bull Researcher and a Bear Researcher.

Your job is to:
1. Weigh both arguments objectively
2. Consider the strength of evidence on each side
3. Deliver a final investment thesis

Consider: Which side presented more data-driven arguments? Which risks are more material?

Respond in valid JSON:
{
    "verdict": "bullish",
    "confidence": 0.7,
    "investment_thesis": "A clear 2-3 paragraph thesis summarizing your conclusion",
    "bull_strength": 0.65,
    "bear_strength": 0.55,
    "key_risks": ["risk1", "risk2"]
}
"""


def _format_reports(state: dict) -> str:
    """Format analyst reports for the researchers."""
    parts = []
    for key in ["market_report", "sentiment_report", "news_report", "fundamentals_report"]:
        report = state.get(key)
        if report:
            r = report if isinstance(report, dict) else report.model_dump()
            parts.append(f"""
--- {r.get('analyst_type', key).upper()} ANALYST REPORT ---
Summary: {r.get('summary', 'N/A')}
Sentiment: {r.get('sentiment', 'N/A')}
Confidence: {r.get('confidence', 'N/A')}
Key Findings: {', '.join(r.get('key_findings', []))}
Reasoning: {r.get('reasoning', 'N/A')}
""")
    return "\n".join(parts) if parts else "No analyst reports available."


def create_bull_researcher(llm, memory=None):
    """Factory for bull researcher node."""

    async def bull_researcher_node(state: dict) -> dict:
        ticker = state["ticker"]
        logger.info(f"🐂 Bull Researcher started for {ticker}")
        reports = _format_reports(state)
        debate = state.get("investment_debate") or InvestmentDebateState()
        if isinstance(debate, dict):
            debate = InvestmentDebateState(**debate)

        # Include bear's last argument if available
        counter = ""
        if debate.bear_arguments:
            last_bear = debate.bear_arguments[-1]
            counter = f"\n\nThe Bear Researcher's latest argument to counter:\n{last_bear.content}"

        # Include memory context
        memory_context = ""
        if memory:
            memories = memory.get_memories(f"{ticker} bullish analysis", n_matches=2)
            if memories:
                memory_context = "\n\nPAST SIMILAR SITUATIONS:\n"
                for m in memories:
                    memory_context += f"- Situation: {m['matched_situation'][:100]}... | Advice: {m['recommendation'][:100]}...\n"

        prompt = f"""
TICKER: {ticker}

ANALYST REPORTS:
{reports}
{counter}
{memory_context}

Make your BULL case.
"""
        messages = [SystemMessage(content=BULL_SYSTEM), HumanMessage(content=prompt)]
        response = await llm.ainvoke(messages)

        result = safe_parse_json(response.content)
        if "raw_response" in result:
            result = {"argument": result["raw_response"], "key_points": [], "conviction": 0.5}

        msg = DebateMessage(speaker="bull", content=result.get("argument", response.content))
        debate.bull_arguments.append(msg)
        debate.round_count = len(debate.bull_arguments)

        logger.info(f"🐂 Bull Researcher done — conviction: {result.get('conviction', 'N/A')}")
        return {"investment_debate": debate}

    return bull_researcher_node


def create_bear_researcher(llm, memory=None):
    """Factory for bear researcher node."""

    async def bear_researcher_node(state: dict) -> dict:
        ticker = state["ticker"]
        logger.info(f"🐻 Bear Researcher started for {ticker}")
        reports = _format_reports(state)
        debate = state.get("investment_debate") or InvestmentDebateState()
        if isinstance(debate, dict):
            debate = InvestmentDebateState(**debate)

        counter = ""
        if debate.bull_arguments:
            last_bull = debate.bull_arguments[-1]
            counter = f"\n\nThe Bull Researcher's latest argument to counter:\n{last_bull.content}"

        memory_context = ""
        if memory:
            memories = memory.get_memories(f"{ticker} bearish risks", n_matches=2)
            if memories:
                memory_context = "\n\nPAST SIMILAR SITUATIONS:\n"
                for m in memories:
                    memory_context += f"- Situation: {m['matched_situation'][:100]}... | Advice: {m['recommendation'][:100]}...\n"

        prompt = f"""
TICKER: {ticker}

ANALYST REPORTS:
{reports}
{counter}
{memory_context}

Make your BEAR case.
"""
        messages = [SystemMessage(content=BEAR_SYSTEM), HumanMessage(content=prompt)]
        response = await llm.ainvoke(messages)

        result = safe_parse_json(response.content)
        if "raw_response" in result:
            result = {"argument": result["raw_response"], "key_points": [], "conviction": 0.5}

        msg = DebateMessage(speaker="bear", content=result.get("argument", response.content))
        debate.bear_arguments.append(msg)

        logger.info(f"🐻 Bear Researcher done — conviction: {result.get('conviction', 'N/A')}")
        return {"investment_debate": debate}

    return bear_researcher_node


def create_research_judge(llm, memory=None):
    """Factory for research manager/judge node."""

    async def research_judge_node(state: dict) -> dict:
        ticker = state["ticker"]
        logger.info(f"⚖️ Research Judge deliberating on {ticker}")
        debate = state.get("investment_debate") or InvestmentDebateState()
        if isinstance(debate, dict):
            debate = InvestmentDebateState(**debate)

        # Format debate history
        debate_history = ""
        for i, (bull, bear) in enumerate(zip(debate.bull_arguments, debate.bear_arguments)):
            debate_history += f"\n--- ROUND {i+1} ---\n"
            debate_history += f"BULL: {bull.content}\n"
            debate_history += f"BEAR: {bear.content}\n"

        prompt = f"""
TICKER: {ticker}

INVESTMENT DEBATE TRANSCRIPT:
{debate_history}

Deliver your verdict.
"""
        messages = [SystemMessage(content=JUDGE_SYSTEM), HumanMessage(content=prompt)]
        response = await llm.ainvoke(messages)

        result = safe_parse_json(response.content)
        if "raw_response" in result:
            result = {"verdict": "neutral", "confidence": 0.5, "investment_thesis": result["raw_response"]}

        debate.judge_verdict = result.get("verdict", "neutral")
        debate.judge_confidence = float(result.get("confidence", 0.5))
        debate.investment_thesis = result.get("investment_thesis", "")

        logger.info(f"⚖️ Research Judge verdict: {debate.judge_verdict} (conf: {debate.judge_confidence:.0%})")
        return {"investment_debate": debate}

    return research_judge_node
