"""
Paper trading execution engine.
Simulates order fills against real-time market data.
Tracks virtual P&L with realistic commission and slippage.
"""
from __future__ import annotations

import datetime as dt
from typing import Dict, List, Optional, Any
from dataclasses import dataclass, field

from app.core.config import settings


@dataclass
class PaperOrder:
    id: str
    asset_id: int
    symbol: str
    action: str          # "buy", "sell"
    order_type: str      # "market", "limit", "stop"
    price: Optional[float]
    size: float
    status: str          # "pending", "filled", "cancelled"
    created_at: dt.datetime
    filled_at: Optional[dt.datetime] = None
    fill_price: Optional[float] = None
    commission: float = 0.0
    slippage: float = 0.0
    pnl: Optional[float] = None


@dataclass
class PaperPosition:
    asset_id: int
    symbol: str
    direction: str       # "long", "short"
    size: float
    avg_entry_price: float
    unrealized_pnl: float = 0.0
    realized_pnl: float = 0.0


@dataclass
class PaperAccount:
    balance: float = 100_000.0
    positions: Dict[int, PaperPosition] = field(default_factory=dict)
    orders: List[PaperOrder] = field(default_factory=list)
    daily_pnl: float = 0.0
    realized_pnl: float = 0.0
    total_trades: int = 0
    win_count: int = 0
    loss_count: int = 0
    max_drawdown: float = 0.0
    peak_balance: float = 100_000.0


class PaperTradingEngine:
    """Simulates fills against live market prices."""

    def __init__(self, initial_balance: float = 100_000.0, on_close=None):
        self.account = PaperAccount(balance=initial_balance)
        self._commission_pct = 0.001
        self._slippage_pct = 0.0005
        self._max_daily_loss_pct = settings.max_daily_loss_pct
        self._max_position_size_pct = settings.max_position_size_pct
        self._on_close = on_close

    def _emit_close(self, pos, fill_price, size, pnl, commission):
        if self._on_close is None:
            return
        self._on_close({
            "asset_id": pos.asset_id,
            "symbol": pos.symbol,
            "direction": pos.direction,
            "entry_price": pos.avg_entry_price,
            "exit_price": fill_price,
            "size": size,
            "pnl": pnl,
            "commission": commission,
            "exit_time": dt.datetime.utcnow(),
        })

    def place_order(self, asset_id: int, symbol: str, action: str, size: float, order_type: str = "market", price: Optional[float] = None) -> PaperOrder:
        """Place a paper order. Market orders fill immediately at last price."""
        order = PaperOrder(
            id=f"paper_{dt.datetime.utcnow().timestamp()}",
            asset_id=asset_id,
            symbol=symbol,
            action=action,
            order_type=order_type,
            price=price,
            size=size,
            status="pending",
            created_at=dt.datetime.utcnow(),
        )
        self.account.orders.append(order)
        return order

    def on_price_update(self, asset_id: int, symbol: str, price: float):
        """Called when a new market price arrives. Fills pending market orders."""
        for order in self.account.orders:
            if order.asset_id != asset_id or order.status != "pending":
                continue

            if order.order_type == "market":
                self._fill_order(order, price)

    def _fill_order(self, order: PaperOrder, market_price: float):
        """Execute a fill with slippage and commission."""
        if order.action == "buy":
            fill_price = market_price * (1 + self._slippage_pct)
        else:
            fill_price = market_price * (1 - self._slippage_pct)

        commission = fill_price * order.size * self._commission_pct
        total_cost = fill_price * order.size + commission

        # Risk guard: max daily loss
        if self.account.daily_pnl < -self.account.balance * (self._max_daily_loss_pct / 100):
            order.status = "cancelled"
            return

        # Risk guard: max position size
        position_value = fill_price * order.size
        if position_value > self.account.balance * (self._max_position_size_pct / 100):
            # Reduce size to fit limit
            max_size = (self.account.balance * (self._max_position_size_pct / 100)) / fill_price
            if max_size <= 0:
                order.status = "cancelled"
                return
            order.size = max_size
            commission = fill_price * order.size * self._commission_pct
            total_cost = fill_price * order.size + commission

        if order.action == "buy":
            if total_cost > self.account.balance:
                order.status = "cancelled"
                return

            self.account.balance -= total_cost

            # Update or create position
            pos = self.account.positions.get(order.asset_id)
            if pos and pos.direction == "long":
                old_value = pos.size * pos.avg_entry_price
                new_value = order.size * fill_price
                total = pos.size + order.size
                pos.avg_entry_price = (old_value + new_value) / total if total > 0 else 0.0
                pos.size = total
            elif pos and pos.direction == "short":
                # Reduce short
                if order.size >= pos.size:
                    # Close short fully
                    pnl = (pos.avg_entry_price - fill_price) * pos.size - commission
                    order.pnl = pnl
                    self.account.realized_pnl += pnl
                    if pnl > 0:
                        self.account.win_count += 1
                    else:
                        self.account.loss_count += 1
                    self._emit_close(pos, fill_price, pos.size, pnl, commission)
                    del self.account.positions[order.asset_id]
                else:
                    pnl = (pos.avg_entry_price - fill_price) * order.size - commission
                    order.pnl = pnl
                    pos.size -= order.size
            else:
                self.account.positions[order.asset_id] = PaperPosition(
                    asset_id=order.asset_id,
                    symbol=order.symbol,
                    direction="long",
                    size=order.size,
                    avg_entry_price=fill_price,
                )
        else:  # sell
            pos = self.account.positions.get(order.asset_id)
            if pos and pos.direction == "long":
                sell_size = min(order.size, pos.size)
                if sell_size <= 0:
                    order.status = "cancelled"
                    return

                pnl = (fill_price - pos.avg_entry_price) * sell_size - commission
                order.pnl = pnl
                self.account.balance += fill_price * sell_size - commission
                pos.size -= sell_size
                if pos.size <= 0:
                    self.account.realized_pnl += pnl
                    if pnl > 0:
                        self.account.win_count += 1
                    else:
                        self.account.loss_count += 1
                    self._emit_close(pos, fill_price, sell_size, pnl, commission)
                    del self.account.positions[order.asset_id]
            else:
                # Opening/increasing short
                self.account.balance += fill_price * order.size - commission
                if pos and pos.direction == "short":
                    old_value = pos.size * pos.avg_entry_price
                    new_value = order.size * fill_price
                    total = pos.size + order.size
                    pos.avg_entry_price = (old_value + new_value) / total if total > 0 else 0.0
                    pos.size = total
                else:
                    self.account.positions[order.asset_id] = PaperPosition(
                        asset_id=order.asset_id,
                        symbol=order.symbol,
                        direction="short",
                        size=order.size,
                        avg_entry_price=fill_price,
                    )

        order.status = "filled"
        order.filled_at = dt.datetime.utcnow()
        order.fill_price = fill_price
        order.commission = commission
        order.slippage = self._slippage_pct
        self.account.total_trades += 1

        # Update peak / drawdown
        if self.account.balance > self.account.peak_balance:
            self.account.peak_balance = self.account.balance
        dd = self.account.peak_balance - self.account.balance
        if dd > self.account.max_drawdown:
            self.account.max_drawdown = dd

    def get_summary(self) -> Dict[str, Any]:
        total_pnl = self.account.realized_pnl
        unrealized = sum(p.unrealized_pnl for p in self.account.positions.values())
        return {
            "balance": round(self.account.balance, 2),
            "equity": round(self.account.balance + unrealized, 2),
            "realized_pnl": round(total_pnl, 2),
            "unrealized_pnl": round(unrealized, 2),
            "total_trades": self.account.total_trades,
            "win_count": self.account.win_count,
            "loss_count": self.account.loss_count,
            "win_rate": round(self.account.win_count / self.account.total_trades, 4) if self.account.total_trades > 0 else 0.0,
            "max_drawdown": round(self.account.max_drawdown, 2),
            "open_positions": len(self.account.positions),
            "peak_balance": round(self.account.peak_balance, 2),
        }
