from __future__ import annotations

import math
from typing import List

from app.data.feeders import OHLCVBar


def sma(bars: List[OHLCVBar], period: int) -> List[dict]:
    if len(bars) < period:
        return []
    result: List[dict] = []
    for i in range(period - 1, len(bars)):
        window = bars[i - period + 1 : i + 1]
        avg = sum(b.close for b in window) / period
        result.append({"timestamp": bars[i].timestamp, "value": avg})
    return result


def ema(bars: List[OHLCVBar], period: int) -> List[dict]:
    if len(bars) < period:
        return []
    alpha = 2.0 / (period + 1)
    # Seed with SMA of first `period` bars
    seed = sum(b.close for b in bars[:period]) / period
    result: List[dict] = []
    prev = seed
    for i in range(period - 1, len(bars)):
        price = bars[i].close
        val = alpha * price + (1 - alpha) * prev
        result.append({"timestamp": bars[i].timestamp, "value": val})
        prev = val
    return result


def rsi(bars: List[OHLCVBar], period: int = 14) -> List[dict]:
    if len(bars) < period + 1:
        return []
    closes = [b.close for b in bars]
    deltas = [closes[i] - closes[i - 1] for i in range(1, len(closes))]
    gains = [d if d > 0 else 0.0 for d in deltas]
    losses = [-d if d < 0 else 0.0 for d in deltas]

    # Initial averages (simple mean over first `period` deltas)
    avg_gain = sum(gains[:period]) / period
    avg_loss = sum(losses[:period]) / period

    result: List[dict] = []
    for i in range(period, len(deltas)):
        avg_gain = (avg_gain * (period - 1) + gains[i]) / period
        avg_loss = (avg_loss * (period - 1) + losses[i]) / period
        if avg_loss == 0:
            rsi_val = 100.0
        else:
            rs = avg_gain / avg_loss
            rsi_val = 100.0 - (100.0 / (1.0 + rs))
        # RSI value corresponds to the bar at index i+1 (since deltas start at 1)
        result.append({"timestamp": bars[i + 1].timestamp, "value": rsi_val})

    return result


def _rolling_std(window: List[float], ddof: int = 1) -> float:
    n = len(window)
    if n <= ddof:
        return math.nan
    mean = sum(window) / n
    variance = sum((x - mean) ** 2 for x in window) / (n - ddof)
    return math.sqrt(variance)


def bollinger(bars: List[OHLCVBar], period: int = 20, std_dev: float = 2.0) -> List[dict]:
    if len(bars) < period:
        return []
    closes = [b.close for b in bars]
    result: List[dict] = []
    for i in range(period - 1, len(bars)):
        window = closes[i - period + 1 : i + 1]
        middle = sum(window) / period
        std = _rolling_std(window, ddof=1)
        if math.isnan(std):
            continue
        result.append({
            "timestamp": bars[i].timestamp,
            "middle": middle,
            "upper": middle + std_dev * std,
            "lower": middle - std_dev * std,
        })
    return result


def macd(
    bars: List[OHLCVBar],
    fast: int = 12,
    slow: int = 26,
    signal: int = 9,
) -> List[dict]:
    if len(bars) < slow + signal:
        return []
    closes = [b.close for b in bars]

    def _ema_series(values: List[float], period: int) -> List[float]:
        alpha = 2.0 / (period + 1)
        seed = sum(values[:period]) / period
        out = [seed]
        for i in range(period, len(values)):
            out.append(alpha * values[i] + (1 - alpha) * out[-1])
        return out

    ema_fast = _ema_series(closes, fast)
    ema_slow = _ema_series(closes, slow)

    # MACD line starts at index slow-1 (where ema_slow has its first value)
    # ema_fast has values starting at index fast-1, but we align from slow-1
    macd_line = [ema_fast[i - (fast - 1)] - ema_slow[i - (slow - 1)] for i in range(slow - 1, len(closes))]

    signal_line_vals = _ema_series(macd_line, signal)

    result: List[dict] = []
    for i in range(signal - 1, len(macd_line)):
        idx = i + (slow - 1)  # corresponding bar index
        macd_val = macd_line[i]
        sig_val = signal_line_vals[i - (signal - 1)]
        result.append({
            "timestamp": bars[idx].timestamp,
            "macd": macd_val,
            "signal": sig_val,
            "histogram": macd_val - sig_val,
        })
    return result
