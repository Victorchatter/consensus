from __future__ import annotations

from typing import Optional, Dict, Any, List

from app.strategies import Strategy, Bar, Signal


class SMACrossStrategy(Strategy):
    """Classic trend-following: buy when fast SMA crosses above slow SMA."""

    name = "SMA Crossover"
    description = "Buys when fast SMA crosses above slow SMA, sells on reverse cross."

    def __init__(self, params: Optional[Dict[str, Any]] = None):
        super().__init__(params)
        self.fast_period = self.params.get("fast_period", 10)
        self.slow_period = self.params.get("slow_period", 30)
        self._closes: List[float] = []

    @property
    def params_schema(self) -> Dict[str, Any]:
        return {
            "fast_period": {"type": "integer", "default": 10, "min": 2, "max": 100},
            "slow_period": {"type": "integer", "default": 30, "min": 5, "max": 200},
        }

    def _sma(self, data: List[float], period: int) -> float:
        if len(data) < period:
            return sum(data) / len(data) if data else 0.0
        return sum(data[-period:]) / period

    def on_bar(self, bar: Bar) -> Optional[Signal]:
        self._bars.append(bar)
        self._closes.append(bar.close)

        if len(self._closes) < self.slow_period + 1:
            return None

        prev_fast = self._sma(self._closes[:-1], self.fast_period)
        prev_slow = self._sma(self._closes[:-1], self.slow_period)
        curr_fast = self._sma(self._closes, self.fast_period)
        curr_slow = self._sma(self._closes, self.slow_period)

        # Golden cross (fast above slow)
        if prev_fast <= prev_slow and curr_fast > curr_slow:
            if self._position != "long":
                self._position = "long"
                return Signal(
                    timestamp=bar.timestamp,
                    action="buy",
                    price=bar.close,
                    metadata={"fast_sma": curr_fast, "slow_sma": curr_slow},
                )

        # Death cross (fast below slow)
        if prev_fast >= prev_slow and curr_fast < curr_slow:
            if self._position != "short":
                self._position = "short"
                return Signal(
                    timestamp=bar.timestamp,
                    action="sell",
                    price=bar.close,
                    metadata={"fast_sma": curr_fast, "slow_sma": curr_slow},
                )

        return None

    def reset(self):
        super().reset()
        self._closes = []
