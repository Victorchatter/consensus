from __future__ import annotations

from typing import Optional, Dict, Any, List
import math

from app.strategies import Strategy, Bar, Signal


class BollingerBreakoutStrategy(Strategy):
    """Breakout using Bollinger Bands. Buys on close above upper band."""

    name = "Bollinger Bands Breakout"
    description = "Buys on close above upper band, sells on close below lower band."

    def __init__(self, params: Optional[Dict[str, Any]] = None):
        super().__init__(params)
        self.period = self.params.get("period", 20)
        self.std_dev = self.params.get("std_dev", 2.0)
        self._closes: List[float] = []

    @property
    def params_schema(self) -> Dict[str, Any]:
        return {
            "period": {"type": "integer", "default": 20, "min": 10, "max": 100},
            "std_dev": {"type": "float", "default": 2.0, "min": 0.5, "max": 5.0},
        }

    def _bands(self, closes: List[float]) -> tuple[Optional[float], Optional[float], Optional[float]]:
        if len(closes) < self.period:
            return None, None, None
        window = closes[-self.period:]
        mean = sum(window) / len(window)
        variance = sum((x - mean) ** 2 for x in window) / len(window)
        std = math.sqrt(variance)
        return mean, mean + self.std_dev * std, mean - self.std_dev * std

    def on_bar(self, bar: Bar) -> Optional[Signal]:
        self._bars.append(bar)
        self._closes.append(bar.close)

        middle, upper, lower = self._bands(self._closes)
        if middle is None:
            return None

        if bar.close > upper and self._position != "long":
            self._position = "long"
            return Signal(
                timestamp=bar.timestamp,
                action="buy",
                price=bar.close,
                metadata={"middle": middle, "upper": upper, "lower": lower},
            )

        if bar.close < lower and self._position != "short":
            self._position = "short"
            return Signal(
                timestamp=bar.timestamp,
                action="sell",
                price=bar.close,
                metadata={"middle": middle, "upper": upper, "lower": lower},
            )

        return None

    def reset(self):
        super().reset()
        self._closes = []
