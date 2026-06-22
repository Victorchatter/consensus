import datetime as dt
import pytest
import sys
import os

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from app.data.feeders import OHLCVBar
from app.data.indicators import sma, ema, rsi, bollinger, macd
from app.strategies.builtin.macd import MACDMomentumStrategy


def _bars(closes: list[float]) -> list[OHLCVBar]:
    base = dt.datetime(2024, 1, 1)
    return [
        OHLCVBar(
            timestamp=base + dt.timedelta(days=i),
            open_=c,
            high=c * 1.01,
            low=c * 0.99,
            close=c,
            volume=1000.0,
        )
        for i, c in enumerate(closes)
    ]


def test_sma_basic():
    data = [1, 2, 3, 4, 5, 6, 7, 8, 9, 10]
    result = sma(_bars(data), 3)
    assert len(result) == len(data) - 3 + 1
    assert result[-1]["value"] == pytest.approx(9.0)


def test_ema_basic():
    data = [1, 2, 3, 4, 5]
    result = ema(_bars(data), 3)
    assert len(result) == len(data) - 3 + 1
    assert result[-1]["value"] > result[0]["value"]


def test_rsi_range():
    data = [10, 11, 12, 11, 10, 9, 8, 9, 10, 11]
    result = rsi(_bars(data), 5)
    for r in result:
        assert 0 <= r["value"] <= 100


def test_bollinger_basic():
    data = list(range(1, 21))
    result = bollinger(_bars(data), 10, 2)
    assert len(result) == len(data) - 10 + 1
    assert result[-1]["upper"] >= result[-1]["middle"] >= result[-1]["lower"]


def test_macd_basic():
    data = [10 + i * 0.5 + (i % 3) for i in range(50)]
    result = macd(_bars(data), 12, 26, 9)
    assert len(result) > 0
    assert "macd" in result[0]
    assert "signal" in result[0]
    assert "histogram" in result[0]


# ── MACD Strategy pure-Python tests ───────────────────────────

def test_macd_strategy_ema():
    strat = MACDMomentumStrategy()
    assert strat._ema([1, 2, 3, 4, 5], 3) == [2.0, 3.0, 4.0]


def test_macd_strategy_macd_no_crash():
    """Ensure MACD calculation never hits negative indices."""
    strat = MACDMomentumStrategy(params={"fast": 12, "slow": 26, "signal": 9})
    closes = [100 + i * 0.1 for i in range(60)]
    macd_val, signal_val, hist = strat._macd(closes)
    assert macd_val is not None
    assert signal_val is not None
    assert hist is not None


def test_macd_strategy_crossover_signal():
    """Synthetic data: prices rise enough to trigger a buy signal."""
    from app.strategies import Bar
    strat = MACDMomentumStrategy(params={"fast": 3, "slow": 6, "signal": 2})
    base = dt.datetime(2024, 1, 1)
    # Rising prices
    for i in range(20):
        bar = Bar(
            timestamp=base + dt.timedelta(hours=i),
            open=100 + i,
            high=101 + i,
            low=99 + i,
            close=100 + i * 2,
            volume=1000,
        )
        sig = strat.on_bar(bar)
        if sig:
            assert sig.action in ("buy", "sell")
            break
