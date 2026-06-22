"""
Behavioural tests for the concrete consensus voters.

Run on a deterministic synthetic uptrend (no network). Asserts the universal
contract (votes are always in {-1, 0, 1}), the default-ensemble shape, that the
trend/breakout voters actually fire long on the uptrend, and that reset()
returns each voter to its warmup state.
"""
from __future__ import annotations

from typing import List

import pytest

from app.strategies import Bar
from app.consensus.base import Voter
from app.consensus.synth import synthetic_bars
from app.consensus.voters import build_default_voters


def _bars() -> List[Bar]:
    """Synthetic uptrend, converted from OHLCVBar to the strategy Bar shape."""
    raw = synthetic_bars(1500, "5m", seed=2, regime="trend")
    return [
        Bar(
            timestamp=b.timestamp,
            open=b.open,
            high=b.high,
            low=b.low,
            close=b.close,
            volume=b.volume or 0.0,
        )
        for b in raw
    ]


def test_votes_always_ternary():
    bars = _bars()
    for voter in build_default_voters():
        for bar in bars:
            v = voter.observe(bar)
            assert v in (-1, 0, 1), f"{voter.name} returned {v!r}"


def test_default_ensemble_is_13_unique_named():
    voters = build_default_voters()
    assert len(voters) == 13
    names = [v.name for v in voters]
    assert len(set(names)) == 13, f"duplicate names: {names}"
    assert all(isinstance(v, Voter) for v in voters)


def test_ma_and_donchian_reach_long_on_uptrend():
    bars = _bars()
    targets = ("ma_5_20", "ma_10_30", "ma_20_50", "ma_50_100",
               "donchian_20", "donchian_55")
    for voter in build_default_voters():
        if voter.name not in targets:
            continue
        votes = [voter.observe(bar) for bar in bars]
        assert 1 in votes, f"{voter.name} never voted +1 on the uptrend"


def test_reset_restores_warmup():
    bars = _bars()
    for voter in build_default_voters():
        # Drive it well past warmup.
        for bar in bars:
            voter.observe(bar)
        voter.reset()
        # First bar after a reset must be in warmup -> abstain.
        assert voter.observe(bars[0]) == 0, (
            f"{voter.name} did not return 0 on first bar after reset"
        )


if __name__ == "__main__":
    raise SystemExit(pytest.main([__file__, "-q"]))
