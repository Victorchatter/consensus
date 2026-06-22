from __future__ import annotations

from .assets import router as assets_router
from .trades import router as trades_router
from .journal import router as journal_router
from .strategies import router as strategies_router
from .backtest import router as backtest_router

__all__ = [
    "assets_router",
    "trades_router",
    "journal_router",
    "strategies_router",
    "backtest_router",
]
