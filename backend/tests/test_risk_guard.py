import datetime as dt
from app.execution.guard import RiskGuard

D1 = dt.datetime(2026, 1, 1, 10, 0)
D2 = dt.datetime(2026, 1, 2, 10, 0)


def test_allows_normal_opening_order():
    g = RiskGuard(max_daily_loss_pct=0.05, max_position_pct=0.20)
    ok, _ = g.check(is_reducing=False, intended_value=1000, equity=100_000, daily_pnl=0, now=D1)
    assert ok


def test_position_cap_rejects_oversized_open():
    g = RiskGuard(0.05, 0.20)
    ok, reason = g.check(False, intended_value=30_000, equity=100_000, daily_pnl=0, now=D1)
    assert not ok and "position" in reason.lower()


def test_latches_on_daily_loss_and_blocks_opens():
    g = RiskGuard(0.05, 0.20)
    ok, reason = g.check(False, 1000, equity=100_000, daily_pnl=-6000, now=D1)
    assert not ok and g.latched
    # stays latched even after pnl recovers, same day
    ok2, _ = g.check(False, 1000, equity=100_000, daily_pnl=0, now=D1)
    assert not ok2


def test_latched_still_allows_closing():
    g = RiskGuard(0.05, 0.20)
    g.check(False, 1000, 100_000, daily_pnl=-6000, now=D1)  # latch
    ok, _ = g.check(is_reducing=True, intended_value=1000, equity=100_000, daily_pnl=-6000, now=D1)
    assert ok


def test_auto_reset_on_utc_day_rollover():
    g = RiskGuard(0.05, 0.20)
    g.check(False, 1000, 100_000, daily_pnl=-6000, now=D1)  # latch on day 1
    ok, _ = g.check(False, 1000, 100_000, daily_pnl=0, now=D2)
    assert ok and not g.latched
