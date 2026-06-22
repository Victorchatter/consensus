"""
Consensus engine core: the Voter protocol, the safety-rail config, and the
ConsensusStrategy that turns many independent votes into one trade signal.

Design: a Voter is *incremental* (`observe(bar) -> -1|0|+1`) exactly like
Strategy.on_bar, so a full backtest is O(n) per voter, not O(n^2). The
ConsensusStrategy is itself a Strategy, so it drops straight into the existing
event-driven BacktestEngine with zero engine changes.
"""
from __future__ import annotations

from abc import ABC, abstractmethod
from dataclasses import dataclass, field
from typing import Dict, List, Optional, Any

from app.strategies import Strategy, Bar, Signal


# ── SAFETY RAILS (Section 1 — enforced in code, not just docs) ──────────────

LIVE_CONFIRMATION_PHRASE = "I ENABLE LIVE TRADING"


@dataclass
class ConsensusConfig:
    # Supermajority magnitude (0..1) the weighted vote must reach to fire.
    threshold: float = 0.6
    # Weighted score at which an open position is closed (hysteresis: enter at
    # +/-threshold, exit at exit_level, so it doesn't flip every bar).
    exit_level: float = 0.0
    allow_short: bool = True

    # Sizing / risk (hard caps independent of Kelly output — Section 1).
    kelly_fraction: float = 0.25
    max_position_pct: float = 0.20
    max_daily_loss_pct: float = 0.05

    # Phase gating.
    min_paper_days: int = 14
    live_trading_enabled: bool = False  # NEVER true by default.

    # Audit: append every per-candle vote breakdown to self.vote_log.
    record_votes: bool = False


def live_trading_allowed(
    config: ConsensusConfig, typed_phrase: str, paper_days_elapsed: float
) -> tuple[bool, str]:
    """Gate for live trading. Must pass ALL three independent checks.

    This is the code-level enforcement of Section 1; the execution loop that
    calls it lands in Phase 3. Returns (allowed, reason).
    """
    if not config.live_trading_enabled:
        return False, "live_trading_enabled is False in config"
    if typed_phrase != LIVE_CONFIRMATION_PHRASE:
        return False, "typed confirmation phrase does not match exactly"
    if paper_days_elapsed < config.min_paper_days:
        return False, (
            f"paper-trading minimum not met: {paper_days_elapsed:.1f}d "
            f"< {config.min_paper_days}d"
        )
    return True, "ok"


# ── VOTER PROTOCOL ──────────────────────────────────────────────────────────


class Voter(ABC):
    """A single independent voter. Stateful and incremental.

    `observe(bar)` is called once per bar in chronological order and returns the
    voter's current directional vote: +1 long, -1 short, 0 flat/abstain.
    """

    name: str = "voter"
    weight: float = 1.0  # overridden by walk-forward-derived weights at runtime.

    @abstractmethod
    def observe(self, bar: Bar) -> int:
        ...

    def reset(self) -> None:
        """Clear per-run state. Override if the voter holds state."""
        return None


# ── CONSENSUS STRATEGY ──────────────────────────────────────────────────────


class ConsensusStrategy(Strategy):
    """Polls N voters each bar, computes a weighted consensus score in [-1, 1],
    and emits long/short/flat signals with the full vote breakdown attached.
    """

    name = "Ensemble Consensus"
    description = "Weighted supermajority vote across independent voters."

    def __init__(
        self,
        voters: List[Voter],
        weights: Optional[Dict[str, float]] = None,
        config: Optional[ConsensusConfig] = None,
    ):
        super().__init__(params=None)
        if not voters:
            raise ValueError("ConsensusStrategy requires at least one voter")
        self.voters = voters
        self.config = config or ConsensusConfig()
        # Default to each voter's own weight; override per-name if provided.
        self.weights: Dict[str, float] = {v.name: max(0.0, float(v.weight)) for v in voters}
        if weights:
            for name, w in weights.items():
                self.weights[name] = max(0.0, float(w))
        self.last_breakdown: Optional[dict] = None
        self.vote_log: List[dict] = []

    def reset(self) -> None:
        super().reset()
        for v in self.voters:
            v.reset()
        self.last_breakdown = None
        self.vote_log = []

    def consensus_score(self, bar: Bar) -> tuple[float, dict]:
        """Collect votes for this bar and return (weighted_score, breakdown)."""
        votes: Dict[str, int] = {}
        weighted_sum = 0.0
        weight_total = 0.0
        for v in self.voters:
            vote = int(v.observe(bar))
            if vote not in (-1, 0, 1):
                vote = 0
            votes[v.name] = vote
            w = self.weights.get(v.name, 0.0)
            weighted_sum += w * vote
            weight_total += w
        score = (weighted_sum / weight_total) if weight_total > 0 else 0.0
        n_long = sum(1 for x in votes.values() if x > 0)
        n_short = sum(1 for x in votes.values() if x < 0)
        n_flat = sum(1 for x in votes.values() if x == 0)
        breakdown = {
            "timestamp": getattr(bar.timestamp, "isoformat", lambda: bar.timestamp)(),
            "score": round(score, 4),
            "n_long": n_long,
            "n_short": n_short,
            "n_flat": n_flat,
            "votes": votes,
        }
        return score, breakdown

    def on_bar(self, bar: Bar) -> Optional[Signal]:
        self._bars.append(bar)
        score, breakdown = self.consensus_score(bar)
        self.last_breakdown = breakdown
        if self.config.record_votes:
            self.vote_log.append(breakdown)

        cfg = self.config
        action: Optional[str] = None
        new_position = self._position

        if self._position is None:
            if score >= cfg.threshold:
                action, new_position = "buy", "long"
            elif cfg.allow_short and score <= -cfg.threshold:
                action, new_position = "sell", "short"
        elif self._position == "long":
            if score <= cfg.exit_level:
                action, new_position = "sell", None
        elif self._position == "short":
            if score >= -cfg.exit_level:
                action, new_position = "buy", None

        if action is None:
            return None

        self._position = new_position
        return Signal(
            timestamp=bar.timestamp,
            action=action,
            price=bar.close,
            metadata=breakdown,
        )
