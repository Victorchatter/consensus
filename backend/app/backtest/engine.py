"""
Event-driven backtest engine.
Replays historical bars bar-by-bar, feeds them to a strategy,
simulates fills with realistic slippage and commission.
"""
from __future__ import annotations

import math
from typing import List, Dict, Any, Optional
from dataclasses import dataclass

from app.backtest import BacktestBar, Fill, BacktestState
from app.strategies import Strategy, Bar, Signal


@dataclass
class ExecutionConfig:
    commission_pct: float = 0.001       # 0.1% per trade
    slippage_pct: float = 0.0005        # 0.05% slippage
    initial_cash: float = 100_000.0
    position_size_pct: float = 0.20   # Use 20% of equity per trade


class BacktestEngine:
    def __init__(self, strategy: Strategy, config: Optional[ExecutionConfig] = None):
        self.strategy = strategy
        self.config = config or ExecutionConfig()
        self.state: BacktestState = BacktestState(cash=self.config.initial_cash)
        self._equity_curve: List[Dict[str, Any]] = []
        self._trades: List[Fill] = []

    def _bar_to_strategy(self, bar: BacktestBar) -> Bar:
        return Bar(
            timestamp=bar.timestamp,
            open=bar.open,
            high=bar.high,
            low=bar.low,
            close=bar.close,
            volume=bar.volume,
        )

    def _simulate_fill(self, signal: Signal, bar: BacktestBar) -> Optional[Fill]:
        """Simulate a market order fill with slippage and commission."""
        if signal.action not in ("buy", "sell"):
            return None

        # Use close price as fill price (realistic for EOD backtest)
        base_price = bar.close

        # Slippage: buy fills slightly higher, sell fills slightly lower
        if signal.action == "buy":
            fill_price = base_price * (1 + self.config.slippage_pct)
        else:
            fill_price = base_price * (1 - self.config.slippage_pct)

        # Determine position size: fixed % of equity
        if signal.action == "buy":
            cash_to_use = self.state.cash * self.config.position_size_pct
            size = cash_to_use / fill_price if fill_price > 0 else 0.0
        else:
            size = self.state.position

        if size <= 0:
            return None

        commission = fill_price * size * self.config.commission_pct
        total_cost = fill_price * size + commission

        if signal.action == "buy":
            if total_cost > self.state.cash:
                # Not enough cash — reduce size
                size = self.state.cash / (fill_price * (1 + self.config.commission_pct))
                if size <= 0:
                    return None
                commission = fill_price * size * self.config.commission_pct
                total_cost = fill_price * size + commission

            # Calculate P&L if reversing from short
            pnl = None
            pnl_pct = None
            if self.state.position < 0:
                pnl = (self.state.avg_entry_price - fill_price) * abs(self.state.position) - commission
                pnl_pct = (pnl / (self.state.avg_entry_price * abs(self.state.position))) * 100 if self.state.avg_entry_price else 0

            self.state.cash -= total_cost
            # Update position: if short, this reduces/eliminates it
            if self.state.position < 0:
                remaining = self.state.position + size
                if remaining >= 0:
                    self.state.position = remaining
                    self.state.avg_entry_price = fill_price if remaining > 0 else 0.0
                else:
                    self.state.position = remaining  # Still short
            else:
                # Average up long position
                old_value = self.state.position * self.state.avg_entry_price
                new_value = size * fill_price
                total = self.state.position + size
                self.state.avg_entry_price = (old_value + new_value) / total if total > 0 else 0.0
                self.state.position = total

            return Fill(
                timestamp=bar.timestamp,
                action="buy",
                price=fill_price,
                size=size,
                commission=commission,
                slippage=self.config.slippage_pct,
                pnl=pnl,
                pnl_pct=pnl_pct,
            )

        else:  # sell
            if self.state.position <= 0 and self.state.position + size <= 0:
                # Selling from short (increasing short)
                pnl = None
                pnl_pct = None
                self.state.cash += fill_price * size - commission
                old_value = abs(self.state.position) * self.state.avg_entry_price
                new_value = size * fill_price
                total = abs(self.state.position) + size
                self.state.avg_entry_price = (old_value + new_value) / total if total > 0 else 0.0
                self.state.position -= size
                return Fill(
                    timestamp=bar.timestamp,
                    action="sell",
                    price=fill_price,
                    size=size,
                    commission=commission,
                    slippage=self.config.slippage_pct,
                    pnl=pnl,
                    pnl_pct=pnl_pct,
                )

            # Closing/reducing long position
            sell_size = min(size, self.state.position)
            if sell_size <= 0:
                return None

            pnl = (fill_price - self.state.avg_entry_price) * sell_size - commission
            pnl_pct = (pnl / (self.state.avg_entry_price * sell_size)) * 100 if self.state.avg_entry_price else 0

            self.state.cash += fill_price * sell_size - commission
            self.state.position -= sell_size
            if self.state.position <= 0:
                self.state.avg_entry_price = 0.0

            return Fill(
                timestamp=bar.timestamp,
                action="sell",
                price=fill_price,
                size=sell_size,
                commission=commission,
                slippage=self.config.slippage_pct,
                pnl=pnl,
                pnl_pct=pnl_pct,
            )

    def run(self, bars: List[BacktestBar]) -> "BacktestResult":
        """Run the backtest over a series of bars."""
        self.strategy.reset()
        self.state = BacktestState(cash=self.config.initial_cash)
        self._equity_curve = []
        self._trades = []

        for bar in bars:
            self.state.current_bar = bar

            # Feed bar to strategy
            strategy_bar = self._bar_to_strategy(bar)
            signal = self.strategy.on_bar(strategy_bar)

            if signal:
                fill = self._simulate_fill(signal, bar)
                if fill:
                    self._trades.append(fill)

            # Record equity at end of bar
            self._equity_curve.append({
                "timestamp": bar.timestamp.isoformat(),
                "equity": self.state.market_value,
                "cash": self.state.cash,
                "position": self.state.position,
                "price": bar.close,
            })

        from app.backtest.metrics import compute_backtest_metrics
        metrics = compute_backtest_metrics(self._equity_curve, self._trades, self.config.initial_cash)

        return BacktestResult(
            equity_curve=self._equity_curve,
            trades=self._trades,
            metrics=metrics,
        )


@dataclass
class BacktestResult:
    equity_curve: List[Dict[str, Any]]
    trades: List[Fill]
    metrics: Dict[str, Any]
