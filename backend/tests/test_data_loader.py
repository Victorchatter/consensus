"""
Regression tests for the canonical bar loader — reproduces the legacy
data-parsing bugs and proves the fix.
"""
from __future__ import annotations

import datetime as dt

import pytest
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker

from app.core.database import Base
from app import models  # noqa: F401 — registers tables on Base
from app.data.feeders import OHLCVBar
from app.data import loader

UTC = dt.timezone.utc
EASTERN = dt.timezone(dt.timedelta(hours=-5))  # fixed offset stand-in for US/Eastern


def _mem_session():
    engine = create_engine("sqlite:///:memory:", connect_args={"check_same_thread": False})
    Base.metadata.create_all(engine)
    return sessionmaker(bind=engine)()


# ── to_utc / normalize ──────────────────────────────────────────────────────


def test_to_utc_naive_assumed_utc():
    naive = dt.datetime(2026, 1, 2, 15, 0, 0)
    assert loader.to_utc(naive) == dt.datetime(2026, 1, 2, 15, 0, 0, tzinfo=UTC)


def test_to_utc_tzaware_converted():
    # 15:00 Eastern (-05:00) is 20:00 UTC — legacy code stored the 15:00 wall
    # clock naively, silently shifting equities vs crypto.
    eastern = dt.datetime(2026, 1, 2, 15, 0, 0, tzinfo=EASTERN)
    assert loader.to_utc(eastern) == dt.datetime(2026, 1, 2, 20, 0, 0, tzinfo=UTC)


def test_normalize_dedups_same_instant_across_tz():
    same_instant_naive = dt.datetime(2026, 1, 2, 20, 0, 0)  # UTC wall clock
    same_instant_aware = dt.datetime(2026, 1, 2, 15, 0, 0, tzinfo=EASTERN)  # == 20:00 UTC
    bars = [
        OHLCVBar(same_instant_naive, 1, 2, 0.5, 1.5, 10),
        OHLCVBar(same_instant_aware, 9, 9, 9, 9, 99),  # later -> wins
    ]
    clean, dupes = loader.normalize_bars(bars)
    assert dupes == 1
    assert len(clean) == 1
    assert clean[0].close == 9  # last write wins


# ── gap detection (session-aware) ───────────────────────────────────────────


def _series(start: dt.datetime, step_min: int, n: int, skip: set[int] | None = None):
    skip = skip or set()
    out = []
    for i in range(n):
        if i in skip:
            continue
        ts = start + dt.timedelta(minutes=step_min * i)
        out.append(OHLCVBar(ts, 100, 101, 99, 100, 1))
    return out


def test_crypto_gap_is_flagged():
    bars = _series(dt.datetime(2026, 1, 1, tzinfo=UTC), 5, 10, skip={4})  # drop one 5m bar
    rep = loader.validate_bars(bars, "5m", "crypto")
    assert rep.n_gaps == 1
    assert rep.gap_details[0]["missing_bars"] == 1


def test_equity_overnight_gap_not_flagged():
    # 1h bars across an overnight boundary on different days -> expected gap.
    day1 = [OHLCVBar(dt.datetime(2026, 1, 2, 20, tzinfo=UTC), 1, 1, 1, 1, 1)]
    day2 = [OHLCVBar(dt.datetime(2026, 1, 5, 14, tzinfo=UTC), 1, 1, 1, 1, 1)]  # next session
    rep = loader.validate_bars(day1 + day2, "1h", "stock")
    assert rep.n_gaps == 0


# ── load_bars boundary (the date-vs-datetime off-by-one) ────────────────────


def test_load_bars_includes_final_day_intraday():
    db = _mem_session()
    asset = models.Asset(symbol="BTCUSDT", asset_class=models.AssetClass.CRYPTO, data_source="binance")
    db.add(asset)
    db.commit()
    db.refresh(asset)

    # Two 5m bars on the end date, one late in the day (23:30) — legacy
    # `timestamp <= date('2026-01-10')` lexical compare dropped these.
    for hh, mm in [(0, 0), (23, 30)]:
        db.add(
            models.PriceBar(
                asset_id=asset.id,
                timestamp=dt.datetime(2026, 1, 10, hh, mm),
                timeframe="5m",
                open=100, high=101, low=99, close=100, volume=1,
            )
        )
    db.commit()

    bars, rep = loader.load_bars(db, asset.id, "5m", dt.date(2026, 1, 1), dt.date(2026, 1, 10))
    assert len(bars) == 2, "final-day 23:30 bar must be included"
    assert rep.n_bars == 2
    assert all(b.timestamp.tzinfo is not None for b in bars)  # UTC-aware on read


def test_load_bars_empty_range_reports_warning():
    db = _mem_session()
    asset = models.Asset(symbol="BTCUSDT", asset_class=models.AssetClass.CRYPTO)
    db.add(asset)
    db.commit()
    db.refresh(asset)
    bars, rep = loader.load_bars(db, asset.id, "5m", dt.date(2026, 1, 1), dt.date(2026, 1, 2))
    assert bars == []
    assert "no bars in range" in rep.warnings


if __name__ == "__main__":
    raise SystemExit(pytest.main([__file__, "-q"]))
