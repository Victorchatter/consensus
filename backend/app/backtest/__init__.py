from __future__ import annotations

from typing import Dict, List, Optional, Any
from dataclasses import dataclass, field
import datetime as dt


@dataclass
class BacktestBar:
    timestamp: dt.datetime
    open: float
    high: float
    low: float
    close: float
    volume: float = 0.0


@dataclass
class Fill:
    timestamp: dt.datetime
    action: str      # "buy", "sell"
    price: float
    size: float
    commission: float
    slippage: float
    pnl: Optional[float] = None
    pnl_pct: Optional[float] = None


@dataclass
class BacktestState:
    cash: float
    position: float = 0.0          # number of units held
    avg_entry_price: float = 0.0
    equity: List[Dict[str, Any]] = field(default_factory=list)
    trades: List[Fill] = field(default_factory=list)
    current_bar: Optional[BacktestBar] = None

    @property
    def market_value(self) -> float:
        if self.current_bar:
            return self.cash + self.position * self.current_bar.close
        return self.cash
