"""
Eligibility ranker for airdrop opportunities.
Uses config/scoring.yaml weights via CONFIG singleton.
"""
import logging
from typing import Dict, List, Optional

from src.config_loader import CONFIG, ScoringConfig

logger = logging.getLogger(__name__)


class EligibilityRanker:
    """
    Ranks protocols by airdrop eligibility score (AOI).
    Scores are composed of weighted sub-scores from the config.
    """

    def __init__(self, config: Optional[ScoringConfig] = None):
        self.weights = (config or CONFIG).eligibility_weights
        self.thresholds = (config or CONFIG).thresholds

    def base_score(self, signal: dict) -> float:
        """Score from TVL, growth, and protocol maturity."""
        score = 0.0
        tvl = signal.get("tvl", 0)
        if tvl > 0:
            score += min(30, int(__import__("math").log10(tvl) * 3))

        growth = signal.get("tvl_growth_7d", 0)
        if growth > 0.5:
            score += 40
        elif growth > 0.1:
            score += 20

        funding = signal.get("funding_raised", 0)
        if funding > 50_000_000:
            score += 30
        elif funding > 10_000_000:
            score += 20

        if signal.get("has_points_program"):
            score += 20

        return min(100.0, score)

    def window_urgency(self, signal: dict) -> float:
        """How urgent is the eligibility window (0-100)."""
        days_until_end = signal.get("days_until_deadline", 365)
        if days_until_end <= 0:
            return 100.0
        if days_until_end <= 7:
            return 100.0
        if days_until_end <= 30:
            return 75.0
        if days_until_end <= 90:
            return 50.0
        return 25.0

    def chain_priority(self, signal: dict) -> float:
        """
        Score based on chain priority tiers.
        Priority 1 chains → 100, Priority 2 → 50, others → 25.
        """
        chain = (signal.get("chain") or "").lower()
        if chain in CONFIG.chains.get("priority_1", []):
            return 100.0
        if chain in CONFIG.chains.get("priority_2", []):
            return 50.0
        return 25.0

    def funding_recency(self, signal: dict) -> float:
        """Score based on how recently the protocol raised funds (0-100)."""
        last_funding_days = signal.get("days_since_last_funding", 999)
        if last_funding_days < 30:
            return 100.0
        if last_funding_days < 90:
            return 75.0
        if last_funding_days < 365:
            return 50.0
        return 25.0

    def tvl_trend_bonus(self, signal: dict) -> float:
        """Score for positive TVL trend (0-100)."""
        growth = signal.get("tvl_growth_7d", 0)
        if growth > 0.5:
            return 100.0
        if growth > 0.1:
            return 50.0
        if growth > 0:
            return 25.0
        return 0.0

    def eligibility_score(self, signal: dict) -> float:
        """Compute composite AOI (Airdrop Opportunity Index) 0–100."""
        bs = self.base_score(signal)
        wu = self.window_urgency(signal)
        cp = self.chain_priority(signal)
        fr = self.funding_recency(signal)
        tb = self.tvl_trend_bonus(signal)

        score = (
            bs * self.weights["base_score"]
            + wu * self.weights["window_urgency"]
            + cp * self.weights["chain_priority"]
            + fr * self.weights["funding_recency"]
            + tb * self.weights["tvl_trend_bonus"]
        )
        return round(min(100.0, score), 1)

    def _urgency_label(self, score: float) -> str:
        if score >= self.thresholds["high_urgency_score"]:
            return "ACT NOW"
        if score >= self.thresholds["medium_urgency_score"]:
            return "WEEKLY"
        return "MONITOR"

    def action_label(self, score: float) -> str:
        label = self._urgency_label(score)
        icons = {"ACT NOW": "\U0001f534", "WEEKLY": "\U0001f7e1", "MONITOR": "\U0001f7e2"}
        return f"{icons.get(label, '')} {label}"

    def explain(self, protocol: dict) -> str:
        """Return human-readable score breakdown."""
        name = protocol.get("name", protocol.get("protocol", "Unknown"))
        bs = self.base_score(protocol)
        wu = self.window_urgency(protocol)
        cp = self.chain_priority(protocol)
        fr = self.funding_recency(protocol)
        tb = self.tvl_trend_bonus(protocol)

        score = (
            bs * self.weights["base_score"]
            + wu * self.weights["window_urgency"]
            + cp * self.weights["chain_priority"]
            + fr * self.weights["funding_recency"]
            + tb * self.weights["tvl_trend_bonus"]
        )
        final = round(min(100.0, score), 1)
        label = self.action_label(final)

        lines = [
            f"Protocol: {name} | AOI: {final}",
            f"\u251c\u2500 base_score:      {bs:>6.1f} \u00d7 {self.weights['base_score']:.2f} = {bs * self.weights['base_score']:.1f}",
            f"\u251c\u2500 window_urgency: {wu:>6.1f} \u00d7 {self.weights['window_urgency']:.2f} = {wu * self.weights['window_urgency']:.1f}",
            f"\u251c\u2500 chain_priority: {cp:>6.1f} \u00d7 {self.weights['chain_priority']:.2f} = {cp * self.weights['chain_priority']:.1f}",
            f"\u251c\u2500 funding_recency: {fr:>6.1f} \u00d7 {self.weights['funding_recency']:.2f} = {fr * self.weights['funding_recency']:.1f}",
            f"\u2514\u2500 tvl_trend_bonus: {tb:>6.1f} \u00d7 {self.weights['tvl_trend_bonus']:.2f} = {tb * self.weights['tvl_trend_bonus']:.1f}",
            f"Final AOI: {final} \u2192 {label}",
        ]
        return "\n".join(lines)

    def rank(self, protocols: List[dict], min_score: float = 0) -> List[dict]:
        """
        Rank protocols by eligibility_score descending.
        Returns annotated list with rank, score, action_label, explain.
        """
        scored = []
        for p in protocols:
            s = self.eligibility_score(p)
            if s < (min_score or self.thresholds.get("min_eligibility_score", 0)):
                continue
            scored.append({
                "protocol": p.get("protocol", p.get("name", "unknown")),
                "name": p.get("name", p.get("protocol", "unknown")),
                "chain": p.get("chain", "unknown"),
                "eligibility_score": s,
                "action_label": self.action_label(s),
                "window_urgency": self._urgency_label(s),
                "base_score": self.base_score(p),
                "explain": self.explain(p),
            })

        scored.sort(key=lambda x: x["eligibility_score"], reverse=True)
        for i, item in enumerate(scored):
            item["rank"] = i + 1
        return scored
