"""
Market Regime Detection — Pure Python implementation (no scikit-learn).
Classifies each day's market as trending, ranging, volatile, or quiet
using rolling volatility and simple trend-strength heuristics.
"""
from __future__ import annotations

import math
from typing import List, Dict, Optional, Tuple
from dataclasses import dataclass


@dataclass
class RegimeResult:
    date: str
    regime_label: str
    volatility_regime: str
    trend_strength: float
    confidence: float
    features: Dict[str, float]


def _mean(values: List[float]) -> float:
    return sum(values) / len(values) if values else 0.0


def _std(values: List[float]) -> float:
    if len(values) < 2:
        return 0.0
    m = _mean(values)
    variance = sum((x - m) ** 2 for x in values) / len(values)
    return math.sqrt(variance)


def detect_regime(closes: List[float], window: int = 20) -> Optional[RegimeResult]:
    """Classify market regime from a series of closing prices."""
    if len(closes) < window + 1:
        return None

    recent = closes[-window:]

    # Volatility = std dev of log returns
    returns = [math.log(recent[i] / recent[i - 1]) for i in range(1, len(recent))]
    vol = _std(returns) * math.sqrt(252)  # Annualized

    # Trend strength = absolute slope of linear regression over window
    x = list(range(len(recent)))
    x_mean = _mean(x)
    y_mean = _mean(recent)
    numerator = sum((x[i] - x_mean) * (recent[i] - y_mean) for i in range(len(recent)))
    denominator = sum((xi - x_mean) ** 2 for xi in x)
    slope = numerator / denominator if denominator != 0 else 0.0
    trend_strength = abs(slope) / y_mean if y_mean != 0 else 0.0

    # Classify volatility
    vol_threshold_high = 0.30
    vol_threshold_low = 0.10
    if vol > vol_threshold_high:
        vol_regime = "high"
    elif vol < vol_threshold_low:
        vol_regime = "low"
    else:
        vol_regime = "normal"

    # Classify overall regime
    if vol > vol_threshold_high and trend_strength > 0.005:
        regime = "volatile"
    elif trend_strength > 0.003:
        regime = "trending"
    elif vol < vol_threshold_low:
        regime = "quiet"
    else:
        regime = "ranging"

    # Confidence = how far we are from decision boundaries
    # Higher = more certain of classification
    confidence = min(1.0, (vol / vol_threshold_high) + (trend_strength / 0.005)) / 2
    confidence = max(0.3, confidence)

    return RegimeResult(
        date="",
        regime_label=regime,
        volatility_regime=vol_regime,
        trend_strength=trend_strength,
        confidence=confidence,
        features={"annualized_volatility": vol, "slope": slope, "mean_price": y_mean},
    )


def batch_detect_regimes(closes: List[float], dates: List[str], window: int = 20) -> List[RegimeResult]:
    """Detect regimes for each day in a price series."""
    results: List[RegimeResult] = []
    for i in range(window, len(closes)):
        r = detect_regime(closes[:i + 1], window)
        if r:
            r.date = dates[i]
            results.append(r)
    return results
