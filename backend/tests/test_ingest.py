"""
Tests for crypto data ingestion — pure / no-network.

Covers the ccxt OHLCV row parser and the source -> feeder routing that gives
crypto a real ccxt feeder instead of falling through to Yahoo.
"""
from __future__ import annotations

import datetime as dt

import pytest
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker

from app.core.database import Base
from app import models  # noqa: F401 — registers tables on Base
from app.data.feeders import (
    parse_ohlcv,
    get_feeder_for_source,
    CCXTFeeder,
    YahooFinanceFeeder,
)
from app.consensus import ingest

UTC = dt.timezone.utc


def _mem_session():
    engine = create_engine(
        "sqlite:///:memory:", connect_args={"check_same_thread": False}
    )
    Base.metadata.create_all(engine)
    return sessionmaker(bind=engine)()


# ── parse_ohlcv ─────────────────────────────────────────────────────────────


def test_parse_ohlcv_two_rows_utc_and_values():
    rows = [
        [1735689600000, 1, 2, 0.5, 1.5, 10],
        [1735689900000, 1.5, 2.5, 1.0, 2.0, 20],
    ]
    bars = parse_ohlcv(rows)
    assert len(bars) == 2

    # 1735689600000 ms == 2025-01-01 00:00:00 UTC
    assert bars[0].timestamp == dt.datetime(2025, 1, 1, 0, 0, 0, tzinfo=UTC)
    assert bars[0].timestamp.tzinfo is not None
    assert bars[0].open == 1.0
    assert bars[0].high == 2.0
    assert bars[0].low == 0.5
    assert bars[0].close == 1.5
    assert bars[0].volume == 10.0

    # +300_000 ms == +5 minutes
    assert bars[1].timestamp == dt.datetime(2025, 1, 1, 0, 5, 0, tzinfo=UTC)
    assert bars[1].close == 2.0
    assert bars[1].volume == 20.0


def test_parse_ohlcv_empty():
    assert parse_ohlcv([]) == []


# ── source -> feeder routing ────────────────────────────────────────────────


def test_binance_source_is_ccxt_feeder():
    feeder = get_feeder_for_source("binance")
    assert isinstance(feeder, CCXTFeeder)
    assert feeder.exchange_id == "binance"


def test_yahoo_source_is_yahoo_feeder():
    assert isinstance(get_feeder_for_source("yahoo"), YahooFinanceFeeder)


def test_ccxt_alias_routes_to_binance():
    feeder = get_feeder_for_source("ccxt")
    assert isinstance(feeder, CCXTFeeder)
    assert feeder.exchange_id == "binance"


def test_unknown_source_falls_back_to_yahoo():
    assert isinstance(get_feeder_for_source("totally-unknown"), YahooFinanceFeeder)


# ── ensure_assets (no network) ──────────────────────────────────────────────


def test_ensure_assets_creates_default_universe():
    db = _mem_session()
    assets = ingest.ensure_assets(db)
    symbols = {a.symbol for a in assets}
    assert {"BTC/USDT", "SPY", "GLD"} <= symbols
    assert db.query(models.Asset).count() == len(ingest.DEFAULT_ASSETS)

    # Idempotent — second call creates nothing new.
    ingest.ensure_assets(db)
    assert db.query(models.Asset).count() == len(ingest.DEFAULT_ASSETS)


if __name__ == "__main__":
    raise SystemExit(pytest.main([__file__, "-q"]))
