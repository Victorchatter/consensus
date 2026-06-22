"""
Backtest performance metrics — pure Python.
"""
from __future__ import annotations

import math
from typing import List, Dict, Any, Optional


def compute_backtest_metrics(
    equity_curve: List[Dict[str, Any]],
    trades: List[Any],
    initial_cash: float,
) -> Dict[str, Any]:
    if not equity_curve:
        return {}

    start_equity = initial_cash
    end_equity = equity_curve[-1]["equity"]
    total_return = (end_equity - start_equity) / start_equity if start_equity else 0.0

    # Daily returns for Sharpe
    equity_values = [e["equity"] for e in equity_curve]
    returns = []
    for i in range(1, len(equity_values)):
        r = (equity_values[i] - equity_values[i - 1]) / equity_values[i - 1] if equity_values[i - 1] else 0.0
        returns.append(r)

    # CAGR (annualized)
    total_days = len(equity_curve)
    cagr = ((end_equity / start_equity) ** (365 / total_days) - 1) if start_equity and total_days > 0 else 0.0

    # Sharpe
    avg_return = sum(returns) / len(returns) if returns else 0.0
    std_return = _std(returns) if returns else 0.0
    sharpe = (avg_return / std_return * math.sqrt(252)) if std_return > 0 else 0.0

    # Sortino
    downside_returns = [r for r in returns if r < 0]
    downside_std = _std(downside_returns) if downside_returns else 0.0
    sortino = (avg_return / downside_std * math.sqrt(252)) if downside_std > 0 else 0.0

    # Max drawdown
    peak = equity_values[0]
    max_dd = 0.0
    max_dd_pct = 0.0
    for val in equity_values:
        if val > peak:
            peak = val
        dd = peak - val
        if dd > max_dd:
            max_dd = dd
            max_dd_pct = (dd / peak * 100) if peak != 0 else 0.0

    # Calmar
    calmar = (cagr / max_dd_pct) if max_dd_pct > 0 else 0.0

    # Trade metrics
    closed_trades = [t for t in trades if t.pnl is not None]
    wins = [t for t in closed_trades if t.pnl > 0]
    losses = [t for t in closed_trades if t.pnl <= 0]
    win_count = len(wins)
    loss_count = len(losses)
    total_trades = len(closed_trades)

    gross_profit = sum(t.pnl for t in wins) if wins else 0.0
    gross_loss = abs(sum(t.pnl for t in losses)) if losses else 0.0

    avg_win = sum(t.pnl for t in wins) / len(wins) if wins else 0.0
    avg_loss = sum(t.pnl for t in losses) / len(losses) if losses else 0.0
    avg_trade = sum(t.pnl for t in closed_trades) / len(closed_trades) if closed_trades else 0.0

    win_rate = win_count / total_trades if total_trades > 0 else 0.0
    profit_factor = gross_profit / gross_loss if gross_loss > 0 else 0.0

    # Expectancy
    expectancy = (win_rate * avg_win) - ((1 - win_rate) * abs(avg_loss)) if total_trades > 0 else 0.0
    expectancy_pct = (expectancy / start_equity * 100) if start_equity else 0.0

    return {
        "total_return": round(total_return, 4),
        "total_return_pct": round(total_return * 100, 2),
        "cagr": round(cagr, 4),
        "cagr_pct": round(cagr * 100, 2),
        "sharpe_ratio": round(sharpe, 2),
        "sortino_ratio": round(sortino, 2),
        "calmar_ratio": round(calmar, 2),
        "max_drawdown": round(max_dd, 2),
        "max_drawdown_pct": round(max_dd_pct, 2),
        "total_trades": total_trades,
        "win_count": win_count,
        "loss_count": loss_count,
        "win_rate": round(win_rate, 4),
        "win_rate_pct": round(win_rate * 100, 1),
        "profit_factor": round(profit_factor, 2),
        "gross_profit": round(gross_profit, 2),
        "gross_loss": round(gross_loss, 2),
        "avg_trade": round(avg_trade, 2),
        "avg_win": round(avg_win, 2),
        "avg_loss": round(avg_loss, 2),
        "expectancy": round(expectancy, 2),
        "expectancy_pct": round(expectancy_pct, 2),
        "best_trade": round(max(t.pnl for t in closed_trades), 2) if closed_trades else None,
        "worst_trade": round(min(t.pnl for t in closed_trades), 2) if closed_trades else None,
    }


def _std(values: List[float]) -> float:
    if len(values) < 2:
        return 0.0
    m = sum(values) / len(values)
    return math.sqrt(sum((x - m) ** 2 for x in values) / len(values))
