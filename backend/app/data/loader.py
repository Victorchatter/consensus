"""
Canonical, validated bar-loading contract.

This is the single source of truth for turning stored PriceBars (or freshly
fetched feeder bars) into a clean, UTC-normalized, gap-checked series. The
consensus engine reads bars ONLY through here so it can never inherit the
legacy data-parsing bugs:

  * feeders returned tz-aware timestamps (Yahoo: exchange-local for equities,
    UTC for crypto; Alpaca: UTC) while PriceBar.timestamp is a naive SQLite
    column that silently dropped tzinfo  -> mixed wall-clock across assets.
  * dedup compared tz-aware == naive  -> never matched  -> duplicates.
  * backtests filtered `timestamp <= end_date` with a `date`  -> lexical
    string compare dropped the final day's intraday bars.

Fix: normalize every timestamp to tz-aware UTC at the boundary, query with
real datetime bounds, dedup/sort deterministically, and report data quality
(gaps/dupes/effective-window) instead of failing silently.
"""
from __future__ import annotations

import datetime as dt
from dataclasses import dataclass, field
from typing import Any, List, Optional, Tuple

from app.data.feeders import OHLCVBar
from app.data.timeframe import tf_seconds, is_intraday

UTC = dt.timezone.utc


def to_utc(value: Any) -> dt.datetime:
    """Coerce a datetime / pandas Timestamp into a tz-aware UTC datetime.

    Naive datetimes are assumed to already be UTC (that is the storage
    convention enforced on write). Anything tz-aware is converted.
    """
    # pandas.Timestamp duck-typing without importing pandas.
    if hasattr(value, "to_pydatetime"):
        value = value.to_pydatetime()
    if not isinstance(value, dt.datetime):
        # Accept date -> midnight UTC.
        if isinstance(value, dt.date):
            value = dt.datetime(value.year, value.month, value.day)
        else:
            value = dt.datetime.fromisoformat(str(value))
    if value.tzinfo is None:
        return value.replace(tzinfo=UTC)
    return value.astimezone(UTC)


def _day_bounds(start: Any, end: Any) -> Tuple[dt.datetime, dt.datetime]:
    """Inclusive [start, end] -> [start_utc, end_utc] datetimes.

    A bare `date` end is expanded to the END of that day so intraday bars on
    the final day are not dropped (the legacy off-by-one).
    """
    start_dt = to_utc(start)
    if isinstance(end, dt.datetime) or hasattr(end, "to_pydatetime"):
        end_dt = to_utc(end)
    else:  # date -> 23:59:59.999999 UTC that day
        d = end if isinstance(end, dt.date) else to_utc(end).date()
        end_dt = dt.datetime(d.year, d.month, d.day, 23, 59, 59, 999999, tzinfo=UTC)
    return start_dt, end_dt


@dataclass
class QualityReport:
    timeframe: str
    asset_class: str
    n_bars: int = 0
    n_duplicates_removed: int = 0
    n_out_of_order: int = 0
    n_gaps: int = 0
    gap_details: List[dict] = field(default_factory=list)
    first_ts: Optional[dt.datetime] = None
    last_ts: Optional[dt.datetime] = None
    warnings: List[str] = field(default_factory=list)

    @property
    def is_clean(self) -> bool:
        return (
            self.n_bars > 0
            and self.n_duplicates_removed == 0
            and self.n_out_of_order == 0
            and self.n_gaps == 0
        )

    def to_dict(self) -> dict:
        return {
            "timeframe": self.timeframe,
            "asset_class": self.asset_class,
            "n_bars": self.n_bars,
            "n_duplicates_removed": self.n_duplicates_removed,
            "n_out_of_order": self.n_out_of_order,
            "n_gaps": self.n_gaps,
            "gap_details": self.gap_details[:50],  # cap for storage
            "first_ts": self.first_ts.isoformat() if self.first_ts else None,
            "last_ts": self.last_ts.isoformat() if self.last_ts else None,
            "is_clean": self.is_clean,
            "warnings": self.warnings,
        }


def normalize_bars(raw_bars: List[OHLCVBar]) -> Tuple[List[OHLCVBar], int]:
    """UTC-normalize, sort ascending, and dedup by timestamp (last wins).

    Returns (clean_bars, n_duplicates_removed).
    """
    by_ts: dict[dt.datetime, OHLCVBar] = {}
    dupes = 0
    for b in raw_bars:
        ts = to_utc(b.timestamp)
        if ts in by_ts:
            dupes += 1
        by_ts[ts] = OHLCVBar(
            timestamp=ts,
            open_=float(b.open),
            high=float(b.high),
            low=float(b.low),
            close=float(b.close),
            volume=None if b.volume is None else float(b.volume),
        )
    clean = [by_ts[ts] for ts in sorted(by_ts)]
    return clean, dupes


def validate_bars(
    bars: List[OHLCVBar], timeframe: str, asset_class: str = "crypto"
) -> QualityReport:
    """Check monotonicity and detect holes against the expected spacing.

    Session-aware gap rule (ponytail: heuristic, not an exchange calendar):
      * crypto trades 24/7 -> ANY delta > 1.5x interval is a real gap.
      * equities/commodities have weekend/overnight gaps that are EXPECTED, so
        for intraday non-crypto we only flag a hole that opens and closes
        within the same UTC day; for daily+ non-crypto we don't gap-check.
      Upgrade path: swap in pandas_market_calendars if calendar precision
      starts to matter.
    """
    report = QualityReport(timeframe=timeframe, asset_class=asset_class, n_bars=len(bars))
    if not bars:
        report.warnings.append("no bars in range")
        return report

    report.first_ts = bars[0].timestamp
    report.last_ts = bars[-1].timestamp

    interval = tf_seconds(timeframe)
    crypto = asset_class == "crypto"
    intraday = is_intraday(timeframe)

    for prev, cur in zip(bars, bars[1:]):
        delta = (cur.timestamp - prev.timestamp).total_seconds()
        if delta <= 0:
            report.n_out_of_order += 1
            continue
        if delta <= interval * 1.5:
            continue  # contiguous
        # There is a hole. Decide whether it's expected.
        expected_session_gap = (not crypto) and (
            not intraday or prev.timestamp.date() != cur.timestamp.date()
        )
        if expected_session_gap:
            continue
        missing = int(round(delta / interval)) - 1
        report.n_gaps += 1
        report.gap_details.append(
            {
                "after": prev.timestamp.isoformat(),
                "before": cur.timestamp.isoformat(),
                "missing_bars": missing,
            }
        )

    if report.n_out_of_order:
        report.warnings.append(f"{report.n_out_of_order} out-of-order timestamps")
    if report.n_gaps:
        report.warnings.append(f"{report.n_gaps} gaps detected")
    return report


def load_bars(
    db,
    asset_id: int,
    timeframe: str,
    start: Any,
    end: Any,
    asset_class: Optional[str] = None,
) -> Tuple[List[OHLCVBar], QualityReport]:
    """Load normalized, validated bars for an asset/timeframe from the DB.

    This is the canonical read path. Returns (bars, quality_report).
    """
    from app import models  # local import to avoid import cycles

    start_dt, end_dt = _day_bounds(start, end)

    if asset_class is None:
        asset = db.query(models.Asset).filter(models.Asset.id == asset_id).first()
        asset_class = (
            getattr(asset.asset_class, "value", asset.asset_class) if asset else "crypto"
        )

    # Query with real datetime bounds (naive-UTC by storage convention). We
    # compare against naive datetimes because SQLite stores naive; to_utc on
    # read re-attaches UTC.
    rows = (
        db.query(models.PriceBar)
        .filter(
            models.PriceBar.asset_id == asset_id,
            models.PriceBar.timeframe == timeframe,
            models.PriceBar.timestamp >= start_dt.replace(tzinfo=None),
            models.PriceBar.timestamp <= end_dt.replace(tzinfo=None),
        )
        .order_by(models.PriceBar.timestamp.asc())
        .all()
    )

    raw = [
        OHLCVBar(
            timestamp=r.timestamp,
            open_=r.open,
            high=r.high,
            low=r.low,
            close=r.close,
            volume=r.volume,
        )
        for r in rows
    ]
    bars, dupes = normalize_bars(raw)
    report = validate_bars(bars, timeframe, asset_class or "crypto")
    report.n_duplicates_removed = dupes
    if dupes:
        report.warnings.append(f"{dupes} duplicate timestamps collapsed")
    return bars, report


def store_timestamp(ts: Any) -> dt.datetime:
    """Normalize a timestamp for WRITING to the DB.

    Storage convention: naive datetime that represents UTC. This is the single
    place writes should funnel through so the naive column stays consistent.
    """
    return to_utc(ts).replace(tzinfo=None)
