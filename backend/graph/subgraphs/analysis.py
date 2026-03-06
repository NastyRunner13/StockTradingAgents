"""
NexusTrade — Analysis Subgraph
Parallel analyst fan-out with dynamic selection via Send API.
"""

from typing import TypedDict, Optional, Any
from langgraph.graph import StateGraph, END
from langgraph.types import Send


# ─── Subgraph State ──────────────────────────────────────────

class AnalysisState(TypedDict):
    """State for the analysis subgraph."""
    ticker: str
    asset_type: str
    trade_date: str
    selected_analysts: list[str]

    # Analyst reports (filled in parallel)
    market_report: Optional[Any]
    sentiment_report: Optional[Any]
    news_report: Optional[Any]
    fundamentals_report: Optional[Any]


# ─── Dynamic Fan-Out Router ─────────────────────────────────

def route_to_analysts(state: dict) -> list[Send]:
    """Dynamically fan-out to selected analysts using Send API."""
    selected = state.get("selected_analysts", ["market", "sentiment", "news", "fundamentals"])
    sends = []
    for analyst in selected:
        sends.append(Send(f"{analyst}_analyst", state))
    return sends


# ─── Merge Node ──────────────────────────────────────────────

async def merge_reports(state: dict) -> dict:
    """No-op merge — state already has all reports from parallel analysts."""
    return {}


# ─── Builder ─────────────────────────────────────────────────

def build_analysis_subgraph(
    market_analyst_node,
    sentiment_analyst_node,
    news_analyst_node,
    fundamentals_analyst_node,
):
    """Build the analysis subgraph with parallel fan-out.
    
    Args:
        market_analyst_node: The market analyst callable
        sentiment_analyst_node: The sentiment analyst callable
        news_analyst_node: The news analyst callable
        fundamentals_analyst_node: The fundamentals analyst callable
    
    Returns:
        Compiled subgraph
    """
    workflow = StateGraph(AnalysisState)

    # Register analyst nodes
    workflow.add_node("market_analyst", market_analyst_node)
    workflow.add_node("sentiment_analyst", sentiment_analyst_node)
    workflow.add_node("news_analyst", news_analyst_node)
    workflow.add_node("fundamentals_analyst", fundamentals_analyst_node)
    workflow.add_node("merge_reports", merge_reports)

    # Dynamic fan-out from START using Send API
    workflow.add_conditional_edges(
        "__start__",
        route_to_analysts,
        [
            "market_analyst",
            "sentiment_analyst",
            "news_analyst",
            "fundamentals_analyst",
        ],
    )

    # All analysts → merge
    workflow.add_edge("market_analyst", "merge_reports")
    workflow.add_edge("sentiment_analyst", "merge_reports")
    workflow.add_edge("news_analyst", "merge_reports")
    workflow.add_edge("fundamentals_analyst", "merge_reports")

    # Merge → END (returns to parent graph)
    workflow.add_edge("merge_reports", END)

    return workflow.compile()
