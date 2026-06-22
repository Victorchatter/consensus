"""Exchange connector factory."""
from __future__ import annotations

from typing import Optional, Dict, Any

from app.exchange.base import ExchangeConnector
from app.exchange.paper import PaperConnector
from app.exchange.alpaca import AlpacaConnector


# Cache of instantiated connectors keyed by connection id
_CONNECTOR_CACHE: Dict[int, ExchangeConnector] = {}


def get_connector(broker_name: str, paper: bool = True, credentials: Optional[Dict[str, Any]] = None) -> ExchangeConnector:
    """Instantiate the right connector for a broker.

    Args:
        broker_name: e.g. 'paper', 'alpaca', 'binance'
        paper: Whether to use paper/sandbox mode
        credentials: Dict with keys like api_key, api_secret, passphrase
    """
    broker_name = broker_name.lower().strip()

    if broker_name == "paper":
        initial = float(credentials.get("initial_balance", 100_000.0)) if credentials else 100_000.0
        return PaperConnector(initial_balance=initial)

    if broker_name == "alpaca":
        if not credentials:
            raise ValueError("Alpaca connector requires credentials")
        return AlpacaConnector(
            api_key=credentials.get("api_key", ""),
            api_secret=credentials.get("api_secret", ""),
            paper=paper,
        )

    raise ValueError(f"Unsupported broker: {broker_name}")


def get_cached_connector(conn_id: int, broker_name: str, paper: bool = True, credentials: Optional[Dict[str, Any]] = None) -> ExchangeConnector:
    """Return a cached connector instance or create a new one."""
    key = conn_id
    if key not in _CONNECTOR_CACHE:
        _CONNECTOR_CACHE[key] = get_connector(broker_name, paper, credentials)
    return _CONNECTOR_CACHE[key]


def clear_connector_cache(conn_id: Optional[int] = None):
    """Clear cached connector(s). Call after updating credentials."""
    if conn_id is None:
        _CONNECTOR_CACHE.clear()
    else:
        _CONNECTOR_CACHE.pop(conn_id, None)
