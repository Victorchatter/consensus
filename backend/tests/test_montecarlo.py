"""
Tests for MonteCarloVoter: determinism, directional edge on a strong uptrend,
and the {-1, 0, 1} vote contract.
"""
from __future__ import annotations

import pytest

from app.consensus.montecarlo import MonteCarloVoter
from app.consensus.synth import synthetic_bars


def _run(voter: MonteCarloVoter, bars) -> list[int]:
    voter.reset()
    return [voter.observe(b) for b in bars]


def test_determinism_same_bars_same_seed():
    bars = synthetic_bars(1200, "5m", seed=3, regime="trend")
    v1 = MonteCarloVoter(seed=7)
    v2 = MonteCarloVoter(seed=7)
    votes1 = _run(v1, bars)
    votes2 = _run(v2, bars)
    assert votes1 == votes2

    # Re-running the same voter object after reset must also reproduce exactly.
    votes3 = _run(v1, bars)
    assert votes1 == votes3


def test_strong_uptrend_produces_long_votes():
    # Heavy positive drift, low noise -> nearly all bootstrap paths finish up.
    bars = synthetic_bars(
        1000, "5m", seed=11, regime="trend", drift=0.002, vol=0.001
    )
    voter = MonteCarloVoter(seed=1)
    votes = _run(voter, bars)
    assert any(v == 1 for v in votes), "expected at least one +1 vote in a strong uptrend"


def test_votes_only_in_valid_set():
    bars = synthetic_bars(800, "5m", seed=5, regime="chop")
    voter = MonteCarloVoter(seed=2)
    votes = _run(voter, bars)
    assert set(votes) <= {-1, 0, 1}


def test_abstains_until_warm():
    bars = synthetic_bars(300, "5m", seed=4, regime="trend")
    voter = MonteCarloVoter(lookback=200, seed=0)
    votes = _run(voter, bars)
    # First `lookback` observations cannot have a full window of returns yet.
    assert all(v == 0 for v in votes[:200])


if __name__ == "__main__":
    raise SystemExit(pytest.main([__file__, "-q"]))
