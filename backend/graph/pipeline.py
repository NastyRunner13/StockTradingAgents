"""
NexusTrade — LangGraph Parallel Agent Pipeline
Key improvement: analysts run in PARALLEL using fan-out, not sequentially.
"""

from typing import TypedDict, Annotated, Optional, Any
from langgraph.graph import StateGraph, END

from llm_client import create_deep_thinker, create_quick_thinker
from agents.analysts import (
    create_market_analyst,
    create_sentiment_analyst,
    create_news_analyst,
    create_fundamentals_analyst,
)
from agents.researchers import (
    create_bull_researcher,
    create_bear_researcher,
    create_research_judge,
)
from agents.traders import (
    create_trader,
    create_aggressive_debater,
    create_conservative_debater,
    create_neutral_debater,
    create_risk_judge,
)
from memory.vector_store import VectorMemory
from config import MAX_DEBATE_ROUNDS, MAX_RISK_DEBATE_ROUNDS


# ─── Pipeline State ───────────────────────────────────────────

class TradingPipelineState(TypedDict):
    """State that flows through the entire pipeline."""
    ticker: str
    asset_type: str
    trade_date: str
    
    # Analyst reports
    market_report: Optional[Any]
    sentiment_report: Optional[Any]
    news_report: Optional[Any]
    fundamentals_report: Optional[Any]
    
    # Debate states
    investment_debate: Optional[Any]
    risk_debate: Optional[Any]
    
    # Trade output
    trade_signal: Optional[Any]
    final_decision: Optional[str]
    trade_approved: bool
    
    # Agent weights
    agent_weights: dict


# ─── Pipeline Builder ─────────────────────────────────────────

class TradingPipeline:
    """Builds and runs the LangGraph agent pipeline."""

    def __init__(self):
        self.quick_llm = create_quick_thinker()
        self.deep_llm = create_deep_thinker()
        self.memory = VectorMemory()

        # Create agent nodes
        self._market = create_market_analyst(self.quick_llm)
        self._sentiment = create_sentiment_analyst(self.quick_llm)
        self._news = create_news_analyst(self.quick_llm)
        self._fundamentals = create_fundamentals_analyst(self.quick_llm)
        
        self._bull = create_bull_researcher(self.quick_llm, self.memory)
        self._bear = create_bear_researcher(self.quick_llm, self.memory)
        self._judge = create_research_judge(self.deep_llm, self.memory)
        
        self._trader = create_trader(self.quick_llm, self.memory)
        
        self._aggressive = create_aggressive_debater(self.quick_llm)
        self._conservative = create_conservative_debater(self.quick_llm)
        self._neutral = create_neutral_debater(self.quick_llm)
        self._risk_judge = create_risk_judge(self.deep_llm, self.memory)

        # Build the graph
        self.graph = self._build_graph()

    def _build_graph(self) -> StateGraph:
        """Build the LangGraph pipeline with parallel analyst fan-out."""
        
        workflow = StateGraph(TradingPipelineState)

        # ─── Analysis Phase (PARALLEL) ─────────────────────────
        # All 4 analysts run at the same time
        workflow.add_node("market_analyst", self._market)
        workflow.add_node("sentiment_analyst", self._sentiment)
        workflow.add_node("news_analyst", self._news)
        workflow.add_node("fundamentals_analyst", self._fundamentals)

        # Merge node collects all analyst results
        async def merge_reports(state: dict) -> dict:
            """No-op merge — state already has all reports from parallel analysts."""
            return {}

        workflow.add_node("merge_reports", merge_reports)

        # ─── Research Debate Phase ─────────────────────────────
        workflow.add_node("bull_researcher", self._bull)
        workflow.add_node("bear_researcher", self._bear)
        workflow.add_node("research_judge", self._judge)

        # ─── Trading Phase ─────────────────────────────────────
        workflow.add_node("trader", self._trader)

        # ─── Risk Debate Phase ─────────────────────────────────
        workflow.add_node("aggressive_analyst", self._aggressive)
        workflow.add_node("conservative_analyst", self._conservative)
        workflow.add_node("neutral_analyst", self._neutral)
        workflow.add_node("risk_judge", self._risk_judge)

        # ─── Edges: Parallel Fan-Out for Analysts ──────────────
        # START → all 4 analysts simultaneously
        workflow.add_edge("__start__", "market_analyst")
        workflow.add_edge("__start__", "sentiment_analyst")
        workflow.add_edge("__start__", "news_analyst")
        workflow.add_edge("__start__", "fundamentals_analyst")

        # All analysts → merge
        workflow.add_edge("market_analyst", "merge_reports")
        workflow.add_edge("sentiment_analyst", "merge_reports")
        workflow.add_edge("news_analyst", "merge_reports")
        workflow.add_edge("fundamentals_analyst", "merge_reports")

        # ─── Edges: Research Debate ────────────────────────────
        workflow.add_edge("merge_reports", "bull_researcher")
        workflow.add_edge("bull_researcher", "bear_researcher")

        # Conditional debate continuation
        def should_continue_debate(state: dict) -> str:
            debate = state.get("investment_debate")
            if debate is None:
                return "research_judge"
            round_count = debate.round_count if hasattr(debate, 'round_count') else debate.get('round_count', 0)
            if round_count < MAX_DEBATE_ROUNDS:
                return "bull_researcher"
            return "research_judge"

        workflow.add_conditional_edges(
            "bear_researcher",
            should_continue_debate,
            {"bull_researcher": "bull_researcher", "research_judge": "research_judge"},
        )

        # ─── Edges: Trading ────────────────────────────────────
        workflow.add_edge("research_judge", "trader")

        # ─── Edges: Risk Debate ────────────────────────────────
        workflow.add_edge("trader", "aggressive_analyst")
        workflow.add_edge("aggressive_analyst", "conservative_analyst")
        workflow.add_edge("conservative_analyst", "neutral_analyst")

        def should_continue_risk(state: dict) -> str:
            debate = state.get("risk_debate")
            if debate is None:
                return "risk_judge"
            round_count = debate.round_count if hasattr(debate, 'round_count') else debate.get('round_count', 0)
            if round_count < MAX_RISK_DEBATE_ROUNDS:
                return "aggressive_analyst"
            return "risk_judge"

        workflow.add_conditional_edges(
            "neutral_analyst",
            should_continue_risk,
            {"aggressive_analyst": "aggressive_analyst", "risk_judge": "risk_judge"},
        )

        workflow.add_edge("risk_judge", END)

        return workflow.compile()

    async def analyze(self, ticker: str, asset_type: str = "stock", trade_date: str = "") -> dict:
        """Run the full pipeline for a ticker.

        Returns the complete final state with trade decision.
        """
        from datetime import datetime
        if not trade_date:
            trade_date = datetime.utcnow().strftime("%Y-%m-%d")

        initial_state: TradingPipelineState = {
            "ticker": ticker,
            "asset_type": asset_type,
            "trade_date": trade_date,
            "market_report": None,
            "sentiment_report": None,
            "news_report": None,
            "fundamentals_report": None,
            "investment_debate": None,
            "risk_debate": None,
            "trade_signal": None,
            "final_decision": None,
            "trade_approved": False,
            "agent_weights": {},
        }

        result = await self.graph.ainvoke(initial_state)
        return result
