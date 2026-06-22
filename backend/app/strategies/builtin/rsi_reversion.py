from __future__ import annotations

from typing import Optional, Dict, Any, List

from app.strategies import Strategy, Bar, Signal


class RSIMeanReversionStrategy(Strategy):
    """Mean reversion using RSI. Buys oversold, sells overbought."""

    name = "RSI Mean Reversion"
    description = "Buys when RSI drops below oversold, sells when RSI rises above overbought."

    def __init__(self, params: Optional[Dict[str, Any]] = None):
        super().__init__(params)
        self.period = self.params.get("period", 14)
        self.oversold = self.params.get("oversold", 30)
        self.overbought = self.params.get("overbought", 70)
        self._closes: List[float] = []

    @property
    def params_schema(self) -> Dict[str, Any]:
        return {
            "period": {"type": "integer", "default": 14, "min": 5, "max": 50},
            "oversold": {"type": "integer", "default": 30, "min": 10, "max": 40},
            "overbought": {"type": "integer", "default": 70, "min": 60, "max": 90},
        }

    def _rsi(self, closes: List[float], period: int) -> Optional[float]:
        if len(closes) < period + 1:
            return None
        deltas = [closes[i] - closes[i - 1] for i in range(1, len(closes))]
        gains = [d if d > 0 else 0 for d in deltas[-period:]]
        losses = [-d if d < 0 else 0 for d in deltas[-period:]]
        avg_gain = sum(gains) / period
        avg_loss = sum(losses) / period
        if avg_loss == 0:
            return 100.0
        rs = avg_gain / avg_loss
        return 100.0 - (100.0 / (1.0 + rs))

    def on_bar(self, bar: Bar) -> Optional[Signal]:
        self._bars.append(bar)
        self._closes.append(bar.close)

        rsi_val = self._rsi(self._closes, self.period)
        if rsi_val is None:
            return None

        if rsi_val < self.oversold and self._position != "long":
            self._position = "long"
            return Signal(
                timestamp=bar.timestamp,
                action="buy",
                price=bar.close,
                metadata={"rsi": rsi_val},
            )

        if rsi_val > self.overbought and self._position != "short":
            self._position = "short"
            return Signal(
                timestamp=bar.timestamp,
                action="sell",
                price=bar.close,
                metadata={"rsi": rsi_val},
            )

        return None

    def reset(self):
        super().reset()
        self._closes = []
