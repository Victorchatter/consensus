"""
Tests for accuracy-derived voter weights (Section 5).

Deterministic synthetic uptrend (no network): a momentum voter should earn a
positive weight, a deliberately wrong contrarian voter should be clamped to 0,
every weight lives in [0, 1], and the result has exactly one entry per voter.
"""
from __future__ import annotations

from typing import List

import pytest

from app.strategies import Bar
from app.consensus.base import Voter
from app.consensus.synth import synthetic_bars
from app.consensus.voters import build_default_voters
from app.consensus.weights import compute_weights


def _bars() -> List[Bar]:
    """Clean synthetic uptrend, converted from OHLCVBar to the strategy Bar shape.

    Strong drift + low vol so the trend dominates bar-to-bar noise: ~70% of
    closes tick up, so an always-short voter is genuinely below chance (and an
    always-long / momentum voter is genuinely above it).
    """
    raw = synthetic_bars(1500, "5m", seed=2, regime="trend", drift=0.0008, vol=0.0015)
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


class _AlwaysShortVoter(Voter):
    """Contrarian fake: always votes -1. On an uptrend it is consistently wrong,
    so its hit rate is below chance and its weight must clamp to 0.0."""

    name = "always_short"
    weight = 1.0

    def observe(self, bar: Bar) -> int:
        return -1

    def reset(self) -> None:
        return None


def test_momentum_voter_gets_positive_weight():
    bars = _bars()
    voters = build_default_voters()
    weights = compute_weights(voters, bars, horizon=1)
    # At least one trend/breakout voter should have found a real edge.
    momentum_names = ("ma_50_100", "donchian_20", "ma_20_50", "donchian_55")
    assert any(weights[name] > 0.0 for name in momentum_names), (
        f"no momentum voter earned a positive weight: "
        f"{ {n: weights[n] for n in momentum_names} }"
    )


def test_all_weights_in_unit_interval():
    bars = _bars()
    weights = compute_weights(build_default_voters(), bars, horizon=1)
    for name, w in weights.items():
        assert 0.0 <= w <= 1.0, f"{name} weight {w} out of [0, 1]"


def test_contrarian_voter_gets_zero_weight():
    bars = _bars()
    voters = build_default_voters() + [_AlwaysShortVoter()]
    weights = compute_weights(voters, bars, horizon=1)
    assert weights["always_short"] == 0.0


def test_one_entry_per_voter_name():
    bars = _bars()
    voters = build_default_voters()
    weights = compute_weights(voters, bars, horizon=1)
    names = [v.name for v in voters]
    assert set(weights.keys()) == set(names)
    assert len(weights) == len(names)


def test_all_zero_falls_back_to_equal_weights():
    """If no voter beats chance, weights degrade to equal (all 1.0), never all-0."""
    bars = _bars()
    # A pair of always-wrong voters in isolation -> every weight would be 0,
    # so the fallback must kick in and return equal weights.
    class _AlsoShort(_AlwaysShortVoter):
        name = "always_short_2"

    weights = compute_weights([_AlwaysShortVoter(), _AlsoShort()], bars, horizon=1)
    assert weights == {"always_short": 1.0, "always_short_2": 1.0}


if __name__ == "__main__":
    raise SystemExit(pytest.main([__file__, "-q"]))
