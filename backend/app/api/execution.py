from __future__ import annotations

from typing import Any
from fastapi import APIRouter

from app.execution.paper import PaperTradingEngine

router = APIRouter(prefix="/paper", tags=["paper-trading"])

# Global paper trading engine instance
engine = PaperTradingEngine(initial_balance=100_000.0)


@router.post("/order")
def place_order(payload: dict) -> dict:
    order = engine.place_order(
        asset_id=payload.get("asset_id", 0),
        symbol=payload.get("symbol", ""),
        action=payload.get("action", "buy"),
        size=payload.get("size", 0.0),
        order_type=payload.get("order_type", "market"),
        price=payload.get("price"),
    )
    return {
        "order_id": order.id,
        "status": order.status,
        "symbol": order.symbol,
        "action": order.action,
        "size": order.size,
    }


@router.post("/price-update")
def price_update(payload: dict) -> dict:
    engine.on_price_update(
        asset_id=payload.get("asset_id", 0),
        symbol=payload.get("symbol", ""),
        price=payload.get("price", 0.0),
    )
    return engine.get_summary()


@router.get("/summary")
def get_summary() -> dict:
    return engine.get_summary()


@router.get("/orders")
def list_orders() -> list:
    return [
        {
            "id": o.id,
            "symbol": o.symbol,
            "action": o.action,
            "size": o.size,
            "status": o.status,
            "fill_price": o.fill_price,
            "pnl": o.pnl,
            "created_at": o.created_at.isoformat(),
        }
        for o in engine.account.orders
    ]
