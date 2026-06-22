"""
Tests for fractional-Kelly position sizing with a hard cap (Section 1 safety).
"""
from __future__ import annotations

import pytest

from app.consensus.sizing import kelly_fraction, kelly_from_trades


# ── kelly_fraction ──────────────────────────────────────────────────────────


def test_under_cap_returns_sized_fraction():
    # full = 0.6 - 0.4/1.0 = 0.2 ; *0.25 = 0.05 ; under cap -> 0.05
    assert kelly_fraction(0.6, 1.0, fraction=0.25, cap=0.20) == pytest.approx(0.05)


def test_huge_edge_is_capped():
    # win_rate ~1, huge payoff -> full ~1, *0.25 = 0.25 > cap -> clamp to cap.
    assert kelly_fraction(0.99, 100.0, fraction=0.25, cap=0.20) == pytest.approx(0.20)
    # Even full Kelly (fraction=1.0) can never exceed the cap.
    assert kelly_fraction(0.99, 100.0, fraction=1.0, cap=0.20) == pytest.approx(0.20)


def test_negative_edge_returns_zero():
    # full = 0.3 - 0.7/1.0 = -0.4 -> negative edge -> floored to 0.0
    assert kelly_fraction(0.3, 1.0, fraction=0.25, cap=0.20) == 0.0


def test_non_positive_ratio_returns_zero():
    assert kelly_fraction(0.6, 0.0) == 0.0
    assert kelly_fraction(0.6, -2.0) == 0.0


# ── kelly_from_trades ───────────────────────────────────────────────────────


def test_empty_trades_returns_zero():
    assert kelly_from_trades([]) == 0.0


def test_all_wins_returns_zero():
    # No losing trades -> downside undefined -> abstain.
    assert kelly_from_trades([10.0, 5.0, 3.0]) == 0.0


def test_all_losses_returns_zero():
    assert kelly_from_trades([-10.0, -5.0, -3.0]) == 0.0


def test_mostly_winning_beats_mostly_losing():
    mostly_winning = [10.0, 12.0, 9.0, 11.0, -5.0]
    mostly_losing = [-10.0, -12.0, -9.0, -11.0, 5.0]
    win_size = kelly_from_trades(mostly_winning)
    lose_size = kelly_from_trades(mostly_losing)
    assert win_size > lose_size
    # Sanity: mostly-winning produces a real position, mostly-losing none.
    assert win_size > 0.0
    assert lose_size == 0.0


def test_result_never_exceeds_cap():
    pnls = [100.0] * 9 + [-1.0]  # 90% win-rate, 100:1 payoff -> enormous edge
    assert kelly_from_trades(pnls, fraction=1.0, cap=0.20) == pytest.approx(0.20)


if __name__ == "__main__":
    raise SystemExit(pytest.main([__file__, "-q"]))
