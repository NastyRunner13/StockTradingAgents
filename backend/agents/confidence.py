"""
NexusTrade — Adaptive Agent Confidence Scoring
Tracks each agent's historical accuracy and adjusts weights.
"""

import math
from datetime import datetime
from models.schemas import AgentAccuracy, TradeAction


class ConfidenceTracker:
    """Tracks and adjusts agent weights based on historical accuracy."""

    def __init__(self):
        self.agents: dict[str, AgentAccuracy] = {}
        self._initialize_agents()

    def _initialize_agents(self):
        """Initialize all agents with default weights."""
        agent_names = [
            "market_analyst", "sentiment_analyst", "news_analyst",
            "fundamentals_analyst", "bull_researcher", "bear_researcher",
            "trader",
        ]
        for name in agent_names:
            self.agents[name] = AgentAccuracy(agent_name=name, weight=1.0)

    def record_prediction(self, agent_name: str, was_correct: bool):
        """Record whether an agent's prediction was correct."""
        if agent_name not in self.agents:
            self.agents[agent_name] = AgentAccuracy(agent_name=agent_name)

        agent = self.agents[agent_name]
        agent.total_predictions += 1
        if was_correct:
            agent.correct_predictions += 1
        
        agent.accuracy = agent.correct_predictions / agent.total_predictions if agent.total_predictions > 0 else 0
        agent.last_updated = datetime.utcnow()

        # Update adaptive weight using EMA-like smoothing
        # New weight = base_weight * (0.5 + accuracy)
        # This means: 50% accuracy = weight 1.0, 80% = 1.3, 20% = 0.7
        agent.weight = round(0.5 + agent.accuracy, 3) if agent.total_predictions >= 5 else 1.0

    def get_weights(self) -> dict[str, float]:
        """Get current agent weights for weighted voting."""
        return {name: agent.weight for name, agent in self.agents.items()}

    def get_weighted_sentiment(self, sentiments: dict[str, str]) -> str:
        """Calculate weighted consensus sentiment from multiple agents."""
        sentiment_scores = {
            "very_bullish": 2, "bullish": 1, "neutral": 0,
            "bearish": -1, "very_bearish": -2,
        }
        
        total_weight = 0
        weighted_score = 0
        
        for agent_name, sentiment in sentiments.items():
            weight = self.agents.get(agent_name, AgentAccuracy(agent_name=agent_name)).weight
            score = sentiment_scores.get(sentiment, 0)
            weighted_score += score * weight
            total_weight += weight

        if total_weight == 0:
            return "neutral"
        
        avg_score = weighted_score / total_weight
        
        if avg_score >= 1.5:
            return "very_bullish"
        elif avg_score >= 0.5:
            return "bullish"
        elif avg_score >= -0.5:
            return "neutral"
        elif avg_score >= -1.5:
            return "bearish"
        else:
            return "very_bearish"

    def kelly_criterion(self, win_rate: float, avg_win: float, avg_loss: float) -> float:
        """Calculate Kelly Criterion optimal position size.
        
        Kelly % = W - [(1-W) / R]
        Where: W = win probability, R = win/loss ratio
        
        Returns fraction of portfolio to risk (capped at 25%).
        """
        if avg_loss == 0 or win_rate <= 0:
            return 0.0

        r = abs(avg_win / avg_loss)
        kelly = win_rate - ((1 - win_rate) / r)
        
        # Half-Kelly for safety (common practice)
        half_kelly = kelly / 2
        
        # Cap at 25% max position
        return max(0.0, min(half_kelly, 0.25))

    def get_stats(self) -> list[dict]:
        """Get all agent statistics."""
        return [agent.model_dump() for agent in self.agents.values()]
