"""
Comprehensive P&L analytics and performance metrics.
Pure Python — no heavy ML dependencies.
"""
from __future__ import annotations

import math
from typing import List, Dict, Optional
from dataclasses import dataclass


@dataclass
class TradeSummary:
    entry_price: float
    exit_price: float
    pnl: float
    pnl_pct: float
    holding_bars: int


@dataclass
class PerformanceReport:
    total_trades: int
    win_count: int
    loss_count: int
    win_rate: float
    profit_factor: float
    gross_profit: float
    gross_loss: float
    total_pnl: float
    avg_trade: float
    avg_win: float
    avg_loss: float
    best_trade: Optional[float]
    worst_trade: Optional[float]
    max_drawdown: float
    max_drawdown_pct: float
    sharpe_ratio: Optional[float]
    sortino_ratio: Optional[float]
    calmar_ratio: Optional[float]
    expectancy: float
    expectancy_pct: float
    consecutive_wins: int
    consecutive_losses: int


def _mean(values: List[float]) -> float:
    return sum(values) / len(values) if values else 0.0


def _std(values: List[float]) -> float:
    if len(values) < 2:
        return 0.0
    m = _mean(values)
    return math.sqrt(sum((x - m) ** 2 for x in values) / len(values))


def compute_performance(trades: List[TradeSummary]) -> PerformanceReport:
    if not trades:
        return PerformanceReport(
            total_trades=0, win_count=0, loss_count=0, win_rate=0.0,
            profit_factor=0.0, gross_profit=0.0, gross_loss=0.0,
            total_pnl=0.0, avg_trade=0.0, avg_win=0.0, avg_loss=0.0,
            best_trade=None, worst_trade=None, max_drawdown=0.0,
            max_drawdown_pct=0.0, sharpe_ratio=None, sortino_ratio=None,
            calmar_ratio=None, expectancy=0.0, expectancy_pct=0.0,
            consecutive_wins=0, consecutive_losses=0,
        )

    wins = [t for t in trades if t.pnl > 0]
    losses = [t for t in trades if t.pnl <= 0]
    win_count = len(wins)
    loss_count = len(losses)
    total = len(trades)

    pnls = [t.pnl for t in trades]
    gross_profit = sum(t.pnl for t in wins) if wins else 0.0
    gross_loss = abs(sum(t.pnl for t in losses)) if losses else 0.0

    # Equity curve for drawdown
    cumulative = []
    running = 0.0
    for t in trades:
        running += t.pnl
        cumulative.append(running)

    peak = 0.0
    max_dd = 0.0
    max_dd_pct = 0.0
    for val in cumulative:
        if val > peak:
            peak = val
        dd = peak - val
        if dd > max_dd:
            max_dd = dd
            max_dd_pct = (dd / peak * 100) if peak != 0 else 0.0

    # Sharpe (annualized, assuming daily trades — rough approximation)
    avg_pnl = _mean(pnls)
    pnl_std = _std(pnls)
    sharpe = (avg_pnl / pnl_std * math.sqrt(252)) if pnl_std > 0 else None

    # Sortino
    downside_returns = [t.pnl for t in trades if t.pnl < 0]
    downside_std = _std(downside_returns) if downside_returns else 0.0
    sortino = (avg_pnl / downside_std * math.sqrt(252)) if downside_std > 0 else None

    # Calmar
    calmar = (avg_pnl * 252 / max_dd) if max_dd > 0 else None

    # Consecutive streaks
    max_consec_wins = 0
    max_consec_losses = 0
    curr_wins = 0
    curr_losses = 0
    for t in trades:
        if t.pnl > 0:
            curr_wins += 1
            curr_losses = 0
            max_consec_wins = max(max_consec_wins, curr_wins)
        else:
            curr_losses += 1
            curr_wins = 0
            max_consec_losses = max(max_consec_losses, curr_losses)

    # Expectancy
    win_rate = win_count / total if total > 0 else 0.0
    avg_win_val = _mean([t.pnl for t in wins]) if wins else 0.0
    avg_loss_val = _mean([t.pnl for t in losses]) if losses else 0.0
    expectancy = (win_rate * avg_win_val) - ((1 - win_rate) * abs(avg_loss_val))
    expectancy_pct = (expectancy / _mean([t.entry_price for t in trades]) * 100) if trades else 0.0

    return PerformanceReport(
        total_trades=total,
        win_count=win_count,
        loss_count=loss_count,
        win_rate=win_rate,
        profit_factor=gross_profit / gross_loss if gross_loss > 0 else 0.0,
        gross_profit=gross_profit,
        gross_loss=gross_loss,
        total_pnl=sum(pnls),
        avg_trade=avg_pnl,
        avg_win=avg_win_val,
        avg_loss=avg_loss_val,
        best_trade=max(pnls) if pnls else None,
        worst_trade=min(pnls) if pnls else None,
        max_drawdown=max_dd,
        max_drawdown_pct=max_dd_pct,
        sharpe_ratio=sharpe,
        sortino_ratio=sortino,
        calmar_ratio=calmar,
        expectancy=expectancy,
        expectancy_pct=expectancy_pct,
        consecutive_wins=max_consec_wins,
        consecutive_losses=max_consec_losses,
    )
