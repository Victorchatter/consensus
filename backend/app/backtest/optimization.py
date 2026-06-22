from __future__ import annotations

import itertools
import datetime as dt
from typing import List, Dict, Any, Optional, Tuple
from dataclasses import dataclass

from app.backtest.engine import BacktestEngine, ExecutionConfig, BacktestResult
from app.backtest import BacktestBar
from app.strategies import Strategy
from app.data.indicators import sma, ema, rsi, bollinger
from app.data.feeders import OHLCVBar


@dataclass
class ParameterGrid:
    params: Dict[str, List[Any]]

    def combinations(self) -> List[Dict[str, Any]]:
        keys = list(self.params.keys())
        values = [self.params[k] for k in keys]
        return [dict(zip(keys, combo)) for combo in itertools.product(*values)]


def run_grid_search(
    strategy_cls: type,
    bars: List[BacktestBar],
    grid: ParameterGrid,
    config: Optional[ExecutionConfig] = None,
    metric: str = "sharpe_ratio",
) -> List[Dict[str, Any]]:
    """Pure-Python grid search over strategy parameters."""
    results = []
    for params in grid.combinations():
        strategy = strategy_cls(params=params)
        engine = BacktestEngine(strategy, config)
        result = engine.run(bars)
        m = result.metrics or {}
        results.append({
            "params": params,
            "metrics": m,
            "score": m.get(metric, float("-inf")),
        })
    results.sort(key=lambda x: x["score"], reverse=True)
    return results


def run_walk_forward(
    strategy_cls: type,
    bars: List[BacktestBar],
    grid: ParameterGrid,
    train_size: int,
    test_size: int,
    config: Optional[ExecutionConfig] = None,
    metric: str = "sharpe_ratio",
) -> Dict[str, Any]:
    """Walk-forward analysis: optimize on train, validate on test, repeat."""
    windows = []
    idx = 0
    while idx + train_size + test_size <= len(bars):
        train_bars = bars[idx : idx + train_size]
        test_bars = bars[idx + train_size : idx + train_size + test_size]

        # Optimize on train
        best = run_grid_search(strategy_cls, train_bars, grid, config, metric)
        best_params = best[0]["params"] if best else {}

        # Run on test with best params
        strategy = strategy_cls(params=best_params)
        engine = BacktestEngine(strategy, config)
        test_result = engine.run(test_bars)

        windows.append({
            "window_index": len(windows) + 1,
            "train_start": train_bars[0].timestamp.isoformat(),
            "train_end": train_bars[-1].timestamp.isoformat(),
            "test_start": test_bars[0].timestamp.isoformat(),
            "test_end": test_bars[-1].timestamp.isoformat(),
            "best_params": best_params,
            "train_score": best[0]["score"] if best else None,
            "test_metrics": test_result.metrics,
        })

        idx += test_size  # Walk forward by test_size

    # Aggregate
    test_scores = [w["test_metrics"].get(metric, float("-inf")) for w in windows if w["test_metrics"]]
    train_scores = [w["train_score"] for w in windows if w["train_score"] is not None]
    degradation = (
        (sum(train_scores) / len(train_scores)) - (sum(test_scores) / len(test_scores))
        if train_scores and test_scores else 0.0
    )

    return {
        "windows": windows,
        "window_count": len(windows),
        "avg_train_score": sum(train_scores) / len(train_scores) if train_scores else None,
        "avg_test_score": sum(test_scores) / len(test_scores) if test_scores else None,
        "degradation": round(degradation, 4),
        "summary": (
            f"{len(windows)} walk-forward windows. "
            f"Avg train {metric}: {sum(train_scores)/len(train_scores):.3f} | "
            f"Avg test {metric}: {sum(test_scores)/len(test_scores):.3f} | "
            f"Degradation: {degradation:.3f}"
        ),
    }


def detect_regime(bars: List[BacktestBar], window: int = 20) -> str:
    """Simple regime detection using rolling volatility and slope."""
    if len(bars) < window + 5:
        return "unknown"
    closes = [b.close for b in bars[-window:]]
    mean = sum(closes) / len(closes)
    variance = sum((c - mean) ** 2 for c in closes) / len(closes)
    std = variance ** 0.5
    cv = std / mean if mean else 0

    # Trend slope via first/last
    slope = (closes[-1] - closes[0]) / window if window > 0 else 0

    if cv > 0.03:
        return "volatile" if abs(slope) > 0.5 else "quiet"
    return "trending" if abs(slope) > 0.5 else "ranging"


def run_regime_aware_backtest(
    strategy_cls: type,
    bars: List[BacktestBar],
    regime_params: Dict[str, Dict[str, Any]],
    config: Optional[ExecutionConfig] = None,
    window: int = 20,
) -> BacktestResult:
    """Run backtest switching parameters based on detected regime."""
    strategy = strategy_cls(params=regime_params.get("default", {}))
    engine = BacktestEngine(strategy, config)
    engine.strategy.reset()
    engine.state.cash = config.initial_cash if config else 100_000.0
    engine._equity_curve = []
    engine._trades = []

    for i, bar in enumerate(bars):
        # Detect regime using recent history
        lookback = bars[max(0, i - window + 1) : i + 1]
        regime = detect_regime(lookback, window=min(window, len(lookback)))

        # Switch params if regime changed and params exist for it
        desired_params = regime_params.get(regime, regime_params.get("default", {}))
        if desired_params != getattr(engine.strategy, "params", {}):
            # Preserve position state across strategy swap (simplified)
            old_position = engine.state.position
            old_avg = engine.state.avg_entry_price
            engine.strategy = strategy_cls(params=desired_params)
            engine.strategy.reset()
            engine.state.position = old_position
            engine.state.avg_entry_price = old_avg

        engine.state.current_bar = bar
        signal = engine.strategy.on_bar(engine._bar_to_strategy(bar))
        if signal:
            fill = engine._simulate_fill(signal, bar)
            if fill:
                engine._trades.append(fill)

        engine._equity_curve.append({
            "timestamp": bar.timestamp.isoformat(),
            "equity": engine.state.market_value,
            "cash": engine.state.cash,
            "position": engine.state.position,
            "price": bar.close,
            "regime": regime,
        })

    from app.backtest.metrics import compute_backtest_metrics
    metrics = compute_backtest_metrics(engine._equity_curve, engine._trades, config.initial_cash if config else 100_000.0)

    return BacktestResult(
        equity_curve=engine._equity_curve,
        trades=engine._trades,
        metrics=metrics,
    )
