"""Exchange connector abstraction layer."""
from __future__ import annotations

import abc
import datetime as dt
from typing import Dict, List, Optional, Any
from dataclasses import dataclass


@dataclass
class AccountInfo:
    balance: float
    buying_power: float
    equity: float
    currency: str = "USD"
    extra: Dict[str, Any] = None

    def __post_init__(self):
        if self.extra is None:
            self.extra = {}


@dataclass
class OrderResult:
    order_id: str
    status: str  # pending, filled, partial, cancelled, rejected
    symbol: str
    side: str    # buy, sell
    size: float
    filled_size: float = 0.0
    fill_price: Optional[float] = None
    commission: float = 0.0
    created_at: Optional[dt.datetime] = None
    extra: Dict[str, Any] = None

    def __post_init__(self):
        if self.extra is None:
            self.extra = {}


@dataclass
class PositionInfo:
    asset_id: int
    symbol: str
    direction: str  # long, short
    size: float
    avg_entry_price: float
    market_price: Optional[float] = None
    unrealized_pnl: float = 0.0
    extra: Dict[str, Any] = None

    def __post_init__(self):
        if self.extra is None:
            self.extra = {}


class ExchangeConnector(abc.ABC):
    """Abstract base for all exchange connectors."""

    def __init__(self, name: str, paper: bool = True):
        self.name = name
        self.paper = paper

    @abc.abstractmethod
    def get_account(self) -> AccountInfo:
        """Return account balance, buying power, equity."""
        ...

    @abc.abstractmethod
    def place_order(
        self,
        asset_id: int,
        symbol: str,
        action: str,
        size: float,
        order_type: str = "market",
        price: Optional[float] = None,
    ) -> OrderResult:
        """Place an order and return its status."""
        ...

    @abc.abstractmethod
    def get_order_status(self, order_id: str) -> OrderResult:
        """Query the current status of an order."""
        ...

    @abc.abstractmethod
    def cancel_order(self, order_id: str) -> bool:
        """Cancel an open order. Returns True if successful."""
        ...

    @abc.abstractmethod
    def get_positions(self) -> List[PositionInfo]:
        """Return all open positions."""
        ...

    def get_quote(self, symbol: str) -> Dict[str, Any]:
        """Optional: fetch latest bid/ask/last. Override if supported."""
        return {}

    def health_check(self) -> Dict[str, Any]:
        """Optional: return connector health. Override if supported."""
        return {"ok": True, "name": self.name, "paper": self.paper}
