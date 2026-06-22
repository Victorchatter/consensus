"""
Ensemble-consensus trading engine (built on EchoTrader's backtest core).

Public surface is intentionally small; concrete voters, Monte Carlo, weights,
sizing and the sweep live in submodules and are imported on demand.
"""
from __future__ import annotations

from app.consensus.base import (
    Voter,
    ConsensusStrategy,
    ConsensusConfig,
    live_trading_allowed,
    LIVE_CONFIRMATION_PHRASE,
)

__all__ = [
    "Voter",
    "ConsensusStrategy",
    "ConsensusConfig",
    "live_trading_allowed",
    "LIVE_CONFIRMATION_PHRASE",
]
