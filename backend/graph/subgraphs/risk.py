"""
NexusTrade — Risk Subgraph
Three-way risk debate (Aggressive, Conservative, Neutral) + Risk Judge.
"""

from typing import TypedDict, Optional, Any
from langgraph.graph import StateGraph, END

from config import MAX_RISK_DEBATE_ROUNDS


# ─── Subgraph State ──────────────────────────────────────────

class RiskState(TypedDict):
    """State for the risk debate subgraph."""
    ticker: str
    asset_type: str
    trade_date: str

    # Trade signal from trader (input)
    trade_signal: Optional[Any]

    # Risk debate state
    risk_debate: Optional[Any]

    # Outputs
    final_decision: Optional[str]
    trade_approved: bool


# ─── Debate Continuation Logic ───────────────────────────────

def should_continue_risk(state: dict) -> str:
    """Decide whether to continue the risk debate or go to the judge."""
    debate = state.get("risk_debate")
    if debate is None:
        return "risk_judge"
    round_count = debate.round_count if hasattr(debate, 'round_count') else debate.get('round_count', 0)
    if round_count < MAX_RISK_DEBATE_ROUNDS:
        return "aggressive_analyst"
    return "risk_judge"


# ─── Builder ─────────────────────────────────────────────────

def build_risk_subgraph(aggressive_node, conservative_node, neutral_node, risk_judge_node):
    """Build the risk debate subgraph.

    Args:
        aggressive_node: Aggressive risk analyst callable
        conservative_node: Conservative risk analyst callable
        neutral_node: Neutral risk analyst callable
        risk_judge_node: Chief Risk Officer judge callable

    Returns:
        Compiled subgraph
    """
    workflow = StateGraph(RiskState)

    workflow.add_node("aggressive_analyst", aggressive_node)
    workflow.add_node("conservative_analyst", conservative_node)
    workflow.add_node("neutral_analyst", neutral_node)
    workflow.add_node("risk_judge", risk_judge_node)

    # START → Aggressive
    workflow.add_edge("__start__", "aggressive_analyst")
    workflow.add_edge("aggressive_analyst", "conservative_analyst")
    workflow.add_edge("conservative_analyst", "neutral_analyst")

    # Neutral → conditional (continue or judge)
    workflow.add_conditional_edges(
        "neutral_analyst",
        should_continue_risk,
        {"aggressive_analyst": "aggressive_analyst", "risk_judge": "risk_judge"},
    )

    # Judge → END
    workflow.add_edge("risk_judge", END)

    return workflow.compile()
