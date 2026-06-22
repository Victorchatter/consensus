"""
Deterministic synthetic OHLCV generator.

Network is not required to validate the consensus harness: tests and the
Phase-1 sweep run on reproducible synthetic series with controllable regime
(trend vs chop) and volatility. Swap in real ingested bars for a tradeable
verdict (see app/consensus/ingest.py).
"""
from __future__ import annotations

import datetime as dt
from typing import List

import numpy as np

from app.data.feeders import OHLCVBar
from app.data.timeframe import tf_seconds

UTC = dt.timezone.utc


def synthetic_bars(
    n: int,
    timeframe: str = "5m",
    seed: int = 0,
    start: dt.datetime | None = None,
    start_price: float = 30000.0,
    drift: float = 0.00002,
    vol: float = 0.004,
    regime: str = "trend",
) -> List[OHLCVBar]:
    """Generate `n` reproducible OHLCV bars.

    regime="trend"  -> persistent drift (momentum voters should find edge)
    regime="chop"   -> mean-reverting (reversion voters favoured, trend hurt)
    """
    rng = np.random.default_rng(seed)
    step = tf_seconds(timeframe)
    if start is None:
        start = dt.datetime(2025, 1, 1, tzinfo=UTC)

    shocks = rng.normal(0.0, vol, size=n)
    closes = np.empty(n)
    price = start_price
    prev_ret = 0.0
    for i in range(n):
        if regime == "chop":
            # mean-revert toward start_price + dampen momentum
            pull = -0.02 * (price - start_price) / start_price
            ret = drift + pull + shocks[i] - 0.3 * prev_ret
        else:  # trend
            ret = drift + shocks[i] + 0.1 * prev_ret
        price *= (1.0 + ret)
        closes[i] = price
        prev_ret = ret

    bars: List[OHLCVBar] = []
    for i in range(n):
        c = float(closes[i])
        o = float(closes[i - 1]) if i > 0 else start_price
        hi = max(o, c) * (1.0 + abs(rng.normal(0, vol / 2)))
        lo = min(o, c) * (1.0 - abs(rng.normal(0, vol / 2)))
        ts = start + dt.timedelta(seconds=step * i)
        vol_units = float(abs(rng.normal(1000, 200)))
        bars.append(OHLCVBar(timestamp=ts, open_=o, high=hi, low=lo, close=c, volume=vol_units))
    return bars


if __name__ == "__main__":
    b = synthetic_bars(2000, "5m", seed=1, regime="trend")
    assert len(b) == 2000
    assert all(b[i].timestamp < b[i + 1].timestamp for i in range(len(b) - 1)), "monotonic"
    assert all(x.high >= x.low for x in b), "high >= low"
    print("synth OK:", b[0].close, "->", b[-1].close)
