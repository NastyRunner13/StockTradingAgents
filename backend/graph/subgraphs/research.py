"""
NexusTrade — Research Subgraph
Bull/Bear adversarial debate with configurable rounds.
"""

from typing import TypedDict, Optional, Any
from langgraph.graph import StateGraph, END

from config import MAX_DEBATE_ROUNDS


# ─── Subgraph State ──────────────────────────────────────────

class ResearchState(TypedDict):
    """State for the research debate subgraph."""
    ticker: str
    asset_type: str
    trade_date: str

    # Analyst reports (read-only input from analysis phase)
    market_report: Optional[Any]
    sentiment_report: Optional[Any]
    news_report: Optional[Any]
    fundamentals_report: Optional[Any]

    # Debate state
    investment_debate: Optional[Any]


# ─── Debate Continuation Logic ───────────────────────────────

def should_continue_debate(state: dict) -> str:
    """Decide whether to continue the bull/bear debate or go to the judge."""
    debate = state.get("investment_debate")
    if debate is None:
        return "research_judge"
    round_count = debate.round_count if hasattr(debate, 'round_count') else debate.get('round_count', 0)
    if round_count < MAX_DEBATE_ROUNDS:
        return "bull_researcher"
    return "research_judge"


# ─── Builder ─────────────────────────────────────────────────

def build_research_subgraph(bull_node, bear_node, judge_node):
    """Build the research debate subgraph.

    Args:
        bull_node: Bull researcher callable
        bear_node: Bear researcher callable
        judge_node: Research judge callable

    Returns:
        Compiled subgraph
    """
    workflow = StateGraph(ResearchState)

    workflow.add_node("bull_researcher", bull_node)
    workflow.add_node("bear_researcher", bear_node)
    workflow.add_node("research_judge", judge_node)

    # START → Bull
    workflow.add_edge("__start__", "bull_researcher")
    workflow.add_edge("bull_researcher", "bear_researcher")

    # Bear → conditional (continue debate or judge)
    workflow.add_conditional_edges(
        "bear_researcher",
        should_continue_debate,
        {"bull_researcher": "bull_researcher", "research_judge": "research_judge"},
    )

    # Judge → END
    workflow.add_edge("research_judge", END)

    return workflow.compile()
