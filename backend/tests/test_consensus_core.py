"""
Money-path tests for the consensus core: weighted threshold crossing,
hysteresis exit, and the live-trading safety gate.
"""
from __future__ import annotations

import datetime as dt

import pytest

from app.strategies import Bar
from app.consensus.base import (
    Voter,
    ConsensusStrategy,
    ConsensusConfig,
    live_trading_allowed,
    LIVE_CONFIRMATION_PHRASE,
)


class FixedVoter(Voter):
    def __init__(self, name: str, direction: int, weight: float = 1.0):
        self.name = name
        self._dir = direction
        self.weight = weight

    def observe(self, bar: Bar) -> int:
        return self._dir


def _bar(price: float = 100.0) -> Bar:
    return Bar(timestamp=dt.datetime(2026, 1, 1, tzinfo=dt.timezone.utc),
               open=price, high=price, low=price, close=price, volume=1)


def test_unanimous_long_fires_buy():
    s = ConsensusStrategy([FixedVoter("a", 1), FixedVoter("b", 1), FixedVoter("c", 1)],
                          config=ConsensusConfig(threshold=0.6))
    sig = s.on_bar(_bar())
    assert sig is not None and sig.action == "buy"
    assert sig.metadata["score"] == 1.0 and sig.metadata["n_long"] == 3


def test_weak_majority_does_not_fire():
    # 2 long, 1 short, equal weight -> score 1/3 < 0.6 threshold.
    s = ConsensusStrategy([FixedVoter("a", 1), FixedVoter("b", 1), FixedVoter("c", -1)],
                          config=ConsensusConfig(threshold=0.6))
    assert s.on_bar(_bar()) is None


def test_weight_overrides_count():
    # 2 light long vs 1 heavy short -> weighted score (1+1-5)/7 = -0.43 -> short.
    s = ConsensusStrategy(
        [FixedVoter("a", 1, 1.0), FixedVoter("b", 1, 1.0), FixedVoter("c", -1, 5.0)],
        config=ConsensusConfig(threshold=0.4, allow_short=True),
    )
    sig = s.on_bar(_bar())
    assert sig is not None and sig.action == "sell"


def test_hysteresis_exit_long():
    voter = FixedVoter("a", 1)
    s = ConsensusStrategy([voter], config=ConsensusConfig(threshold=0.6, exit_level=0.0))
    assert s.on_bar(_bar()).action == "buy"   # enter long
    voter._dir = 0                            # consensus collapses to neutral
    sig = s.on_bar(_bar())
    assert sig is not None and sig.action == "sell"  # exit at exit_level
    assert s._position is None


def test_no_short_when_disabled():
    s = ConsensusStrategy([FixedVoter("a", -1), FixedVoter("b", -1)],
                          config=ConsensusConfig(threshold=0.6, allow_short=False))
    assert s.on_bar(_bar()) is None


def test_vote_log_records_every_bar_when_enabled():
    s = ConsensusStrategy([FixedVoter("a", 0)], config=ConsensusConfig(record_votes=True))
    for _ in range(5):
        s.on_bar(_bar())
    assert len(s.vote_log) == 5


# ── safety gate ─────────────────────────────────────────────────────────────


def test_live_blocked_by_default():
    ok, reason = live_trading_allowed(ConsensusConfig(), LIVE_CONFIRMATION_PHRASE, 30)
    assert not ok and "config" in reason


def test_live_blocked_wrong_phrase():
    cfg = ConsensusConfig(live_trading_enabled=True)
    ok, _ = live_trading_allowed(cfg, "i enable live trading", 30)
    assert not ok


def test_live_blocked_insufficient_paper_days():
    cfg = ConsensusConfig(live_trading_enabled=True, min_paper_days=14)
    ok, reason = live_trading_allowed(cfg, LIVE_CONFIRMATION_PHRASE, 3)
    assert not ok and "paper" in reason


def test_live_allowed_when_all_pass():
    cfg = ConsensusConfig(live_trading_enabled=True, min_paper_days=14)
    ok, reason = live_trading_allowed(cfg, LIVE_CONFIRMATION_PHRASE, 20)
    assert ok and reason == "ok"


if __name__ == "__main__":
    raise SystemExit(pytest.main([__file__, "-q"]))
