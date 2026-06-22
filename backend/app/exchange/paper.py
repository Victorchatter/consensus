"""Paper trading connector — wraps the existing paper engine."""
from __future__ import annotations

import datetime as dt
from typing import Dict, List, Optional, Any

from app.exchange.base import ExchangeConnector, AccountInfo, OrderResult, PositionInfo
from app.execution.paper import PaperTradingEngine


class PaperConnector(ExchangeConnector):
    """Paper trading connector that simulates fills against market prices."""

    def __init__(self, initial_balance: float = 100_000.0):
        super().__init__(name="paper", paper=True)
        self._engine = PaperTradingEngine(initial_balance=initial_balance)

    def get_account(self) -> AccountInfo:
        summary = self._engine.get_summary()
        return AccountInfo(
            balance=summary.get("balance", 0.0),
            buying_power=summary.get("equity", 0.0),
            equity=summary.get("equity", 0.0),
            extra=summary,
        )

    def place_order(
        self,
        asset_id: int,
        symbol: str,
        action: str,
        size: float,
        order_type: str = "market",
        price: Optional[float] = None,
    ) -> OrderResult:
        paper_order = self._engine.place_order(
            asset_id=asset_id,
            symbol=symbol,
            action=action,
            size=size,
            order_type=order_type,
            price=price,
        )
        # Paper engine market orders fill immediately on next price update
        # Fill now if we have a price hint
        if order_type == "market" and price is not None:
            self._engine.on_price_update(asset_id, symbol, price)
        return OrderResult(
            order_id=paper_order.id,
            status=paper_order.status,
            symbol=paper_order.symbol,
            side=paper_order.action,
            size=paper_order.size,
            filled_size=paper_order.size if paper_order.status == "filled" else 0.0,
            fill_price=paper_order.fill_price,
            commission=paper_order.commission,
            created_at=paper_order.created_at,
        )

    def get_order_status(self, order_id: str) -> OrderResult:
        for o in self._engine.account.orders:
            if o.id == order_id:
                return OrderResult(
                    order_id=o.id,
                    status=o.status,
                    symbol=o.symbol,
                    side=o.action,
                    size=o.size,
                    filled_size=o.size if o.status == "filled" else 0.0,
                    fill_price=o.fill_price,
                    commission=o.commission,
                    created_at=o.created_at,
                )
        return OrderResult(
            order_id=order_id,
            status="not_found",
            symbol="",
            side="",
            size=0.0,
        )

    def cancel_order(self, order_id: str) -> bool:
        for o in self._engine.account.orders:
            if o.id == order_id and o.status == "pending":
                o.status = "cancelled"
                return True
        return False

    def get_positions(self) -> List[PositionInfo]:
        return [
            PositionInfo(
                asset_id=p.asset_id,
                symbol=p.symbol,
                direction=p.direction,
                size=p.size,
                avg_entry_price=p.avg_entry_price,
                unrealized_pnl=p.unrealized_pnl,
            )
            for p in self._engine.account.positions.values()
        ]

    def on_price_update(self, asset_id: int, symbol: str, price: float):
        """Feed a price tick into the paper engine so pending market orders fill."""
        self._engine.on_price_update(asset_id, symbol, price)

    def get_summary(self) -> Dict[str, Any]:
        """Expose full paper account summary for the bot state."""
        return self._engine.get_summary()
