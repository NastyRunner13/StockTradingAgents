"""
NexusTrade — LangGraph Pipeline v2
Subgraph architecture + Checkpointing + Human-in-the-Loop + Dynamic Analyst Selection
"""

from typing import TypedDict, Optional, Any
from langgraph.graph import StateGraph, END
from langgraph.types import interrupt, Send
from langgraph.checkpoint.sqlite.aio import AsyncSqliteSaver
import aiosqlite
import logging

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
from config import (
    MAX_DEBATE_ROUNDS,
    MAX_RISK_DEBATE_ROUNDS,
    CHECKPOINT_DB_PATH,
    ENABLE_HITL,
    AUTO_TRADE_CONFIDENCE,
    DEFAULT_ANALYSTS,
)

logger = logging.getLogger("nexustrade.pipeline")


# ─── Pipeline State ───────────────────────────────────────────

class TradingPipelineState(TypedDict):
    """State that flows through the entire pipeline."""
    ticker: str
    asset_type: str
    trade_date: str
    selected_analysts: list[str]

    # Analyst reports
    market_report: Optional[Any]
    sentiment_report: Optional[Any]
    news_report: Optional[Any]
    fundamentals_report: Optional[Any]

    analysis_id: Optional[str]
    
    # Debate states
    investment_debate: Optional[Any]
    risk_debate: Optional[Any]

    # Trade output
    trade_signal: Optional[Any]
    final_decision: Optional[str]
    trade_approved: bool

    # Agent weights
    agent_weights: dict


# ─── Dynamic Analyst Fan-Out ──────────────────────────────────

ANALYST_MAP = {
    "market": "market_analyst",
    "sentiment": "sentiment_analyst",
    "news": "news_analyst",
    "fundamentals": "fundamentals_analyst",
}


def route_to_analysts(state: dict) -> list[Send]:
    """Dynamically fan-out to selected analysts using Send API."""
    selected = state.get("selected_analysts", DEFAULT_ANALYSTS)
    sends = []
    for analyst_key in selected:
        node_name = ANALYST_MAP.get(analyst_key)
        if node_name:
            sends.append(Send(node_name, state))
    if not sends:
        # Fallback: run all analysts
        for node_name in ANALYST_MAP.values():
            sends.append(Send(node_name, state))
    return sends


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


def should_continue_risk(state: dict) -> str:
    """Decide whether to continue the risk debate or go to the judge."""
    debate = state.get("risk_debate")
    if debate is None:
        return "risk_judge"
    round_count = debate.round_count if hasattr(debate, 'round_count') else debate.get('round_count', 0)
    if round_count < MAX_RISK_DEBATE_ROUNDS:
        return "aggressive_analyst"
    return "risk_judge"


# ─── HITL Approval Node ──────────────────────────────────────

async def human_approval_node(state: dict) -> dict:
    """Human-in-the-loop node: pauses for trade approval if conditions met.

    High-confidence trades (>= AUTO_TRADE_CONFIDENCE) are auto-approved.
    Lower-confidence trades require manual approval via the interrupt() API.
    """
    if not ENABLE_HITL:
        logger.info("⚡ HITL disabled — auto-approving trade")
        return {"trade_approved": True, "final_decision": "auto_approved_hitl_disabled"}

    trade_signal = state.get("trade_signal")
    if trade_signal is None:
        return {"trade_approved": False, "final_decision": "no_trade_signal"}

    confidence = (
        trade_signal.confidence
        if hasattr(trade_signal, "confidence")
        else trade_signal.get("confidence", 0)
    )

    if confidence >= AUTO_TRADE_CONFIDENCE:
        logger.info(f"⚡ Auto-approving trade (confidence {confidence:.0%} >= {AUTO_TRADE_CONFIDENCE:.0%})")
        return {"trade_approved": True, "final_decision": "auto_approved_high_confidence"}

    # Pause for human approval
    logger.info(f"⏸️  Pausing for human approval (confidence {confidence:.0%})")

    approval = interrupt({
        "type": "trade_approval_required",
        "trade_signal": trade_signal if isinstance(trade_signal, dict) else {
            "action": getattr(trade_signal, "action", "unknown"),
            "confidence": confidence,
            "entry_price": getattr(trade_signal, "entry_price", None),
            "target_price": getattr(trade_signal, "target_price", None),
            "stop_loss": getattr(trade_signal, "stop_loss", None),
            "position_size_pct": getattr(trade_signal, "position_size_pct", None),
            "reasoning": getattr(trade_signal, "reasoning", ""),
        },
        "message": f"Trade requires approval (confidence: {confidence:.0%}). Reply with 'approve' or 'reject'.",
    })

    approved = str(approval).strip().lower() in ("approve", "approved", "yes", "true", "1")
    decision = "human_approved" if approved else "human_rejected"
    logger.info(f"{'✅' if approved else '❌'} Human decision: {decision}")

    return {"trade_approved": approved, "final_decision": decision}


# ─── Merge Node ──────────────────────────────────────────────

async def merge_reports(state: dict) -> dict:
    """No-op merge — state already has all reports from parallel analysts."""
    return {}


# ─── Pipeline Builder ─────────────────────────────────────────

class TradingPipeline:
    """Builds and runs the LangGraph agent pipeline with subgraph composition."""

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

        # Checkpointer — initialized async in initialize()
        self._checkpointer = None
        self.graph = None

    async def initialize(self):
        """Async init: create the aiosqlite-backed checkpointer and compile the graph."""
        conn = await aiosqlite.connect(str(CHECKPOINT_DB_PATH))
        self._checkpointer = AsyncSqliteSaver(conn)
        self.graph = self._build_graph()

    def _build_graph(self):
        """Build the composed pipeline: Analysis → Research → Trader → Risk → Approval."""

        workflow = StateGraph(TradingPipelineState)

        # ─── Analysis Phase (PARALLEL via Send API) ─────────────
        workflow.add_node("market_analyst", self._market)
        workflow.add_node("sentiment_analyst", self._sentiment)
        workflow.add_node("news_analyst", self._news)
        workflow.add_node("fundamentals_analyst", self._fundamentals)
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

        # ─── HITL Approval Phase ───────────────────────────────
        workflow.add_node("human_approval", human_approval_node)

        # ─── Edges: Dynamic Parallel Fan-Out for Analysts ──────
        # START → dynamically selected analysts via Send API
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

        # ─── Edges: Research Debate ────────────────────────────
        workflow.add_edge("merge_reports", "bull_researcher")
        workflow.add_edge("bull_researcher", "bear_researcher")

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

        workflow.add_conditional_edges(
            "neutral_analyst",
            should_continue_risk,
            {"aggressive_analyst": "aggressive_analyst", "risk_judge": "risk_judge"},
        )

        # ─── Risk Judge → HITL Approval → END ─────────────────
        workflow.add_edge("risk_judge", "human_approval")
        workflow.add_edge("human_approval", END)

        return workflow.compile(checkpointer=self._checkpointer)

    async def analyze(
        self,
        ticker: str,
        asset_type: str = "stock",
        trade_date: str = "",
        log_callback=None,
        selected_analysts: list[str] | None = None,
        thread_id: str | None = None,
        analysis_id: str = "",
    ) -> dict:
        """Run the full pipeline for a ticker.

        Args:
            ticker: Stock or crypto ticker symbol
            asset_type: "stock" or "crypto"
            trade_date: Date for the analysis
            log_callback: Optional async callback(agent, stage, message, details)
            selected_analysts: Which analysts to run (default: all)
            thread_id: Thread ID for checkpointing (auto-generated if None)

        Returns the complete final state with trade decision.
        """
        from datetime import datetime
        import uuid

        if not trade_date:
            trade_date = datetime.utcnow().strftime("%Y-%m-%d")

        if thread_id is None:
            thread_id = str(uuid.uuid4())

        analysts = selected_analysts or DEFAULT_ANALYSTS

        initial_state: TradingPipelineState = {
            "ticker": ticker,
            "asset_type": asset_type,
            "trade_date": trade_date,
            "selected_analysts": analysts,
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
            "analysis_id": analysis_id,
        }

        config = {
            "configurable": {
                "thread_id": thread_id,
                "_log_callback": log_callback,
            }
        }

        logger.info(f"🚀 Starting analysis for {ticker} (thread: {thread_id}, analysts: {analysts})")

        result = await self.graph.ainvoke(initial_state, config=config)
        return {**result, "thread_id": thread_id}

    async def resume(self, thread_id: str, approval: str) -> dict:
        """Resume a paused pipeline (after HITL interrupt).

        Args:
            thread_id: The thread_id from the paused analysis
            approval: 'approve' or 'reject'

        Returns the complete final state after resuming.
        """
        config = {"configurable": {"thread_id": thread_id}}
        logger.info(f"▶️  Resuming thread {thread_id} with approval: {approval}")

        result = await self.graph.ainvoke(
            None,  # No new input — resume from checkpoint
            config=config,
        )
        return {**result, "thread_id": thread_id}

    async def get_state(self, thread_id: str) -> dict | None:
        """Get the current state of a pipeline thread.

        Args:
            thread_id: The thread_id to retrieve state for

        Returns the current state or None if thread doesn't exist.
        """
        config = {"configurable": {"thread_id": thread_id}}
        try:
            snapshot = await self.graph.aget_state(config)
            if snapshot and snapshot.values:
                state = dict(snapshot.values)
                return {
                    **state,
                    "thread_id": thread_id,
                    "status": "interrupted" if snapshot.next else "completed",
                    "next_nodes": list(snapshot.next) if snapshot.next else [],
                }
        except Exception as e:
            logger.error(f"Error getting state for thread {thread_id}: {e}")
        return None
