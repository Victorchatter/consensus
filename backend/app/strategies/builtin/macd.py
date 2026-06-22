from __future__ import annotations

from typing import Optional, Dict, Any, List

from app.strategies import Strategy, Bar, Signal


class MACDMomentumStrategy(Strategy):
    """Momentum strategy using MACD histogram crossover."""

    name = "MACD Momentum"
    description = "Buys on bullish MACD crossover, sells on bearish."

    def __init__(self, params: Optional[Dict[str, Any]] = None):
        super().__init__(params)
        self.fast = self.params.get("fast", 12)
        self.slow = self.params.get("slow", 26)
        self.signal = self.params.get("signal", 9)
        self._closes: List[float] = []

    @property
    def params_schema(self) -> Dict[str, Any]:
        return {
            "fast": {"type": "integer", "default": 12, "min": 5, "max": 50},
            "slow": {"type": "integer", "default": 26, "min": 10, "max": 100},
            "signal": {"type": "integer", "default": 9, "min": 5, "max": 50},
        }

    def _ema(self, data: List[float], period: int) -> List[float]:
        if len(data) < period:
            return []
        ema_vals = []
        multiplier = 2 / (period + 1)
        ema_vals.append(sum(data[:period]) / period)
        for price in data[period:]:
            ema_vals.append((price - ema_vals[-1]) * multiplier + ema_vals[-1])
        return ema_vals

    def _macd(self, closes: List[float]) -> tuple[Optional[float], Optional[float], Optional[float]]:
        ema_fast = self._ema(closes, self.fast)
        ema_slow = self._ema(closes, self.slow)
        if not ema_fast or not ema_slow:
            return None, None, None

        # Both EMAs end at the latest close. ema_fast is longer because fast < slow.
        # Align from the end by taking the overlapping tail of ema_fast.
        fast_aligned = ema_fast[-len(ema_slow):]
        macd_line = [f - s for f, s in zip(fast_aligned, ema_slow)]

        signal_line = self._ema(macd_line, self.signal)
        if not signal_line:
            return None, None, None

        # Align signal_line to macd_line from the end.
        macd_aligned = macd_line[-len(signal_line):]
        histogram = [m - s for m, s in zip(macd_aligned, signal_line)]

        return macd_line[-1], signal_line[-1], histogram[-1]

    def on_bar(self, bar: Bar) -> Optional[Signal]:
        self._bars.append(bar)
        self._closes.append(bar.close)

        macd_val, signal_val, hist = self._macd(self._closes)
        if macd_val is None:
            return None

        # Need previous histogram for crossover detection
        if len(self._closes) < self.slow + self.signal + 2:
            return None

        prev_closes = self._closes[:-1]
        prev_macd, prev_signal, prev_hist = self._macd(prev_closes)
        if prev_hist is None:
            return None

        if hist > 0 and prev_hist <= 0 and self._position != "long":
            self._position = "long"
            return Signal(
                timestamp=bar.timestamp,
                action="buy",
                price=bar.close,
                metadata={"macd": macd_val, "signal": signal_val, "histogram": hist},
            )

        if hist < 0 and prev_hist >= 0 and self._position != "short":
            self._position = "short"
            return Signal(
                timestamp=bar.timestamp,
                action="sell",
                price=bar.close,
                metadata={"macd": macd_val, "signal": signal_val, "histogram": hist},
            )

        return None

    def reset(self):
        super().reset()
        self._closes = []
