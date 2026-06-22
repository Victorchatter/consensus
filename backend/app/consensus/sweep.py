"""
Walk-forward consensus-threshold sweep with realistic fees + slippage
(Section 6).

The sweep slides non-overlapping [train | test] windows across a bar series.
On each fold it derives accuracy-based voter weights from the *train* slice
(`compute_weights`), then runs the consensus strategy out-of-sample on the
*test* slice for every candidate threshold, through the real BacktestEngine so
commissions and slippage hit every fill. Per-threshold OOS performance is then
aggregated across all folds, and the best threshold is the one with the highest
risk-adjusted (Sharpe) score, breaking ties on higher compounded return.

Network is never touched: callers pass synthetic (or pre-ingested) bars.
"""
from __future__ import annotations

from typing import Any, Dict, List, Optional, Sequence, Tuple

from app.backtest import BacktestBar
from app.backtest.engine import BacktestEngine, ExecutionConfig
from app.backtest.metrics import compute_backtest_metrics
from app.consensus.base import ConsensusConfig, ConsensusStrategy
from app.consensus.montecarlo import MonteCarloVoter
from app.consensus.voters import build_default_voters
from app.consensus.weights import compute_weights
from app.strategies import Bar


# ── default fee schedule by asset class (round-trip-ish per-fill commission) ──

_DEFAULT_COMMISSION: Dict[str, float] = {
    "crypto": 0.001,
    "stock": 0.0005,
    "etf": 0.0005,
    "commodity": 0.0003,
}


def _commission_for(asset_class: str) -> float:
    return _DEFAULT_COMMISSION.get((asset_class or "").lower(), 0.001)


# ── conversions ───────────────────────────────────────────────────────────────


def ohlcv_to_bars(ohlcv_list: Sequence[Any]) -> List[Bar]:
    """Convert OHLCVBar-like objects to strategy Bars (copy fields)."""
    out: List[Bar] = []
    for b in ohlcv_list:
        out.append(
            Bar(
                timestamp=b.timestamp,
                open=float(b.open),
                high=float(b.high),
                low=float(b.low),
                close=float(b.close),
                volume=float(b.volume) if getattr(b, "volume", None) is not None else 0.0,
            )
        )
    return out


def ohlcv_to_backtest_bars(ohlcv_list: Sequence[Any]) -> List[BacktestBar]:
    """Convert OHLCVBar-like objects to BacktestBars (copy fields)."""
    out: List[BacktestBar] = []
    for b in ohlcv_list:
        out.append(
            BacktestBar(
                timestamp=b.timestamp,
                open=float(b.open),
                high=float(b.high),
                low=float(b.low),
                close=float(b.close),
                volume=float(b.volume) if getattr(b, "volume", None) is not None else 0.0,
            )
        )
    return out


# ── fold-level metric extraction ──────────────────────────────────────────────


def _metric(metrics: Dict[str, Any], *keys: str) -> float:
    """Pull the first present metric key, defaulting to 0.0."""
    for k in keys:
        if k in metrics and metrics[k] is not None:
            try:
                return float(metrics[k])
            except (TypeError, ValueError):
                return 0.0
    return 0.0


def _avg_trade_bars(equity_len: int, n_trades: int) -> float:
    """Crude average holding period proxy: bars per trade."""
    if n_trades <= 0:
        return 0.0
    return float(equity_len) / float(n_trades)


def _run_fold(
    threshold: float,
    train_bars: List[Bar],
    test_backtest_bars: List[BacktestBar],
    weights: Dict[str, float],
    commission_pct: float,
    slippage_pct: float,
    seed: int,
) -> Optional[Dict[str, float]]:
    """Run one (threshold, fold) backtest OOS. Returns per-fold stats or None."""
    voters = build_default_voters() + [MonteCarloVoter(seed=seed)]
    strategy = ConsensusStrategy(
        voters,
        weights,
        ConsensusConfig(threshold=threshold),
    )
    engine = BacktestEngine(
        strategy,
        ExecutionConfig(commission_pct=commission_pct, slippage_pct=slippage_pct),
    )
    result = engine.run(test_backtest_bars)

    metrics = result.metrics or {}
    if not metrics:
        metrics = compute_backtest_metrics(
            result.equity_curve, result.trades, ExecutionConfig().initial_cash
        )

    n_trades = int(_metric(metrics, "total_trades"))
    ret_pct = _metric(metrics, "total_return_pct")
    return {
        "return_frac": ret_pct / 100.0,
        "total_return_pct": ret_pct,
        "sharpe": _metric(metrics, "sharpe_ratio"),
        "sortino": _metric(metrics, "sortino_ratio"),
        "max_drawdown_pct": _metric(metrics, "max_drawdown_pct"),
        "win_rate": _metric(metrics, "win_rate"),
        "n_trades": float(n_trades),
        "avg_trade_bars": _avg_trade_bars(len(result.equity_curve), n_trades),
    }


# ── public API ────────────────────────────────────────────────────────────────


def run_threshold_sweep(
    bars: Sequence[Any],
    asset_class: str = "crypto",
    timeframe: str = "5m",
    symbol: str = "SYNTH",
    thresholds: Tuple[float, ...] = (0.5, 0.6, 0.7, 0.8, 0.9),
    train_size: int = 300,
    test_size: int = 150,
    commission_pct: Optional[float] = None,
    slippage_pct: float = 0.0005,
    seed: int = 0,
) -> Dict[str, Any]:
    """Walk-forward sweep over consensus thresholds with realistic costs.

    Returns the dict shape documented in the Phase-1 spec.
    """
    if commission_pct is None:
        commission_pct = _commission_for(asset_class)

    n_bars = len(bars)

    # Accumulators per threshold across folds.
    acc: Dict[float, Dict[str, Any]] = {
        t: {
            "compounded": 1.0,
            "sharpes": [],
            "sortinos": [],
            "worst_dd": 0.0,
            "win_weighted": 0.0,  # win_rate * n_trades
            "n_trades": 0,
            "avg_trade_bars_weighted": 0.0,  # avg_trade_bars * n_trades
            "folds": 0,
        }
        for t in thresholds
    }

    n_folds = 0
    start = 0
    step = max(1, int(test_size))
    while start + train_size + test_size <= n_bars:
        train_slice = bars[start : start + train_size]
        test_slice = bars[start + train_size : start + train_size + test_size]
        n_folds += 1

        try:
            train_bars = ohlcv_to_bars(train_slice)
            test_backtest_bars = ohlcv_to_backtest_bars(test_slice)

            # Accuracy-derived weights from the in-sample slice.
            weight_voters = build_default_voters() + [MonteCarloVoter(seed=seed)]
            weights = compute_weights(weight_voters, train_bars)

            for t in thresholds:
                try:
                    fold = _run_fold(
                        t,
                        train_bars,
                        test_backtest_bars,
                        weights,
                        commission_pct,
                        slippage_pct,
                        seed,
                    )
                except Exception:
                    fold = None
                if fold is None:
                    continue
                a = acc[t]
                a["compounded"] *= (1.0 + fold["return_frac"])
                a["sharpes"].append(fold["sharpe"])
                a["sortinos"].append(fold["sortino"])
                a["worst_dd"] = max(a["worst_dd"], fold["max_drawdown_pct"])
                nt = int(fold["n_trades"])
                a["win_weighted"] += fold["win_rate"] * nt
                a["avg_trade_bars_weighted"] += fold["avg_trade_bars"] * nt
                a["n_trades"] += nt
                a["folds"] += 1
        except Exception:
            # One bad fold must not kill the sweep.
            continue

        start += step

    # Aggregate.
    per_threshold: Dict[str, Dict[str, Any]] = {}
    for t in thresholds:
        a = acc[t]
        sharpes = a["sharpes"]
        sortinos = a["sortinos"]
        mean_sharpe = sum(sharpes) / len(sharpes) if sharpes else 0.0
        mean_sortino = sum(sortinos) / len(sortinos) if sortinos else 0.0
        total_return_pct = (a["compounded"] - 1.0) * 100.0
        n_trades = int(a["n_trades"])
        win_rate = (a["win_weighted"] / n_trades) if n_trades > 0 else 0.0
        avg_trade_bars = (
            a["avg_trade_bars_weighted"] / n_trades if n_trades > 0 else 0.0
        )
        per_threshold[str(t)] = {
            "threshold": float(t),
            "total_return_pct": round(total_return_pct, 2),
            "sharpe": round(mean_sharpe, 4),
            "sortino": round(mean_sortino, 4),
            "max_drawdown_pct": round(a["worst_dd"], 2),
            "win_rate": round(win_rate, 4),
            "n_trades": n_trades,
            "avg_trade_bars": round(avg_trade_bars, 2),
        }

    # Best threshold: max Sharpe, tie-break higher return.
    best_threshold = float(thresholds[0]) if thresholds else 0.0
    best_key: Optional[Tuple[float, float]] = None
    for t in thresholds:
        pt = per_threshold[str(t)]
        key = (pt["sharpe"], pt["total_return_pct"])
        if best_key is None or key > best_key:
            best_key = key
            best_threshold = float(t)

    return {
        "timeframe": timeframe,
        "asset_class": asset_class,
        "symbol": symbol,
        "n_bars": n_bars,
        "n_folds": n_folds,
        "per_threshold": per_threshold,
        "best_threshold": best_threshold,
        "data_quality": {
            "n_bars": n_bars,
            "n_folds": n_folds,
            "train_size": int(train_size),
            "test_size": int(test_size),
            "commission_pct": float(commission_pct),
            "slippage_pct": float(slippage_pct),
        },
    }


def run_multi(datasets: List[Dict[str, Any]]) -> List[Dict[str, Any]]:
    """Run `run_threshold_sweep` over a list of dataset descriptors.

    Each dataset is a dict with keys: bars (required) and optional
    asset_class, timeframe, symbol (plus any other run_threshold_sweep kwarg).
    """
    results: List[Dict[str, Any]] = []
    for ds in datasets:
        kwargs = {k: v for k, v in ds.items() if k != "bars"}
        results.append(run_threshold_sweep(ds["bars"], **kwargs))
    return results


__all__ = [
    "ohlcv_to_bars",
    "ohlcv_to_backtest_bars",
    "run_threshold_sweep",
    "run_multi",
]
