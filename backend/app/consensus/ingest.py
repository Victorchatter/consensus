"""
Data ingestion: fetch OHLCV bars from a source feeder and persist them as
``models.PriceBar`` rows, then hand back a quality report from the canonical
loader.

This is the write-side counterpart to ``app.data.loader.load_bars`` (the read
side). Crypto now has a real ccxt feeder (see ``app.data.feeders.CCXTFeeder``);
previously crypto symbols fell through to Yahoo, which mangled their symbols.

NOTHING here touches the network at import time. ``ensure_assets`` only writes
asset rows; ``ingest_bars`` is the only thing that calls a feeder.
"""
from __future__ import annotations

import datetime as dt
from typing import Any, List

from app.data.feeders import get_feeder_for_source
from app.data.loader import load_bars, store_timestamp, QualityReport

# Default universe seeded by ``ensure_assets``. Crypto goes through ccxt
# (binance); equities/commodities stay on Yahoo.
DEFAULT_ASSETS: List[dict] = [
    {"symbol": "BTC/USDT", "asset_class": "crypto", "data_source": "binance"},
    {"symbol": "SPY", "asset_class": "etf", "data_source": "yahoo"},
    {"symbol": "GLD", "asset_class": "commodity", "data_source": "yahoo"},
]


def ensure_assets(db) -> list:
    """Create the ``DEFAULT_ASSETS`` rows that don't exist yet.

    Returns the full list of ``models.Asset`` rows for the default universe
    (existing + newly created). Does NOT call the network.
    """
    from app import models  # local import to avoid import cycles

    assets = []
    created = False
    for spec in DEFAULT_ASSETS:
        existing = (
            db.query(models.Asset)
            .filter(models.Asset.symbol == spec["symbol"])
            .first()
        )
        if existing is None:
            existing = models.Asset(
                symbol=spec["symbol"],
                asset_class=models.AssetClass(spec["asset_class"]),
                data_source=spec["data_source"],
            )
            db.add(existing)
            created = True
        assets.append(existing)
    if created:
        db.commit()
        for a in assets:
            db.refresh(a)
    return assets


def ingest_bars(
    db,
    asset_id: int,
    symbol: str,
    asset_class: str,
    data_source: str,
    timeframe: str,
    start: Any,
    end: Any,
) -> QualityReport:
    """Fetch bars for ``symbol`` and upsert them as PriceBars, then validate.

    Steps:
      1. resolve the feeder for ``data_source`` and fetch historical bars,
      2. upsert each bar by (asset_id, timestamp, timeframe), normalizing the
         timestamp through ``store_timestamp`` (naive-UTC storage convention),
      3. return the ``QualityReport`` produced by the canonical read path.
    """
    from app import models  # local import to avoid import cycles

    feeder = get_feeder_for_source(data_source)
    raw_bars = feeder.fetch_historical(symbol, start, end, timeframe)

    for bar in raw_bars:
        ts = store_timestamp(bar.timestamp)
        existing = (
            db.query(models.PriceBar)
            .filter(
                models.PriceBar.asset_id == asset_id,
                models.PriceBar.timestamp == ts,
                models.PriceBar.timeframe == timeframe,
            )
            .first()
        )
        if existing is None:
            db.add(
                models.PriceBar(
                    asset_id=asset_id,
                    timestamp=ts,
                    timeframe=timeframe,
                    open=float(bar.open),
                    high=float(bar.high),
                    low=float(bar.low),
                    close=float(bar.close),
                    volume=None if bar.volume is None else float(bar.volume),
                )
            )
        else:
            existing.open = float(bar.open)
            existing.high = float(bar.high)
            existing.low = float(bar.low)
            existing.close = float(bar.close)
            existing.volume = None if bar.volume is None else float(bar.volume)
    db.commit()

    _, report = load_bars(db, asset_id, timeframe, start, end, asset_class)
    return report


def _infer_spec(symbol: str, source: str | None, asset_class: str | None) -> tuple[str, str]:
    """Resolve (data_source, asset_class) for a symbol.

    Known DEFAULT_ASSETS win; otherwise guess by symbol shape and let explicit
    --source / --asset-class flags override.
    # ponytail: shape heuristic ("/" -> crypto on ccxt), override with flags.
    """
    for spec in DEFAULT_ASSETS:
        if spec["symbol"] == symbol:
            return source or spec["data_source"], asset_class or spec["asset_class"]
    if "/" in symbol:
        return source or "binance", asset_class or "crypto"
    return source or "yahoo", asset_class or "stock"


def main(argv: list[str] | None = None) -> int:
    """CLI: ingest real OHLCV bars on a networked machine.

    Example:
      python -m app.consensus.ingest --symbol BTC/USDT --source binance \\
          --timeframe 5m --start 2023-01-01 --end 2025-01-01
    """
    import argparse

    from app.core.database import SessionLocal
    from app import models

    p = argparse.ArgumentParser(
        prog="python -m app.consensus.ingest",
        description="Ingest real OHLCV bars into EchoTrader for the consensus engine.",
    )
    p.add_argument("--symbol", required=True, help='e.g. "BTC/USDT", "SPY", "GLD"')
    p.add_argument("--timeframe", default="5m")
    p.add_argument("--start", required=True, help="ISO date YYYY-MM-DD")
    p.add_argument("--end", required=True, help="ISO date YYYY-MM-DD")
    p.add_argument("--source", default=None, help="override data_source (binance/kraken/yahoo/alpaca)")
    p.add_argument("--asset-class", dest="asset_class", default=None)
    args = p.parse_args(argv)

    src, acls = _infer_spec(args.symbol, args.source, args.asset_class)
    start = dt.date.fromisoformat(args.start)
    end = dt.date.fromisoformat(args.end)

    db = SessionLocal()
    try:
        asset = db.query(models.Asset).filter(models.Asset.symbol == args.symbol).first()
        if asset is None:
            asset = models.Asset(
                symbol=args.symbol,
                asset_class=models.AssetClass(acls),
                data_source=src,
            )
            db.add(asset)
            db.commit()
            db.refresh(asset)
        report = ingest_bars(db, asset.id, args.symbol, acls, src, args.timeframe, start, end)
        rd = report.to_dict()
        print(
            f"[ingest] {args.symbol} {args.timeframe}: {rd['n_bars']} bars "
            f"({rd['first_ts']} -> {rd['last_ts']}) "
            f"dupes={rd['n_duplicates_removed']} gaps={rd['n_gaps']} clean={rd['is_clean']}"
        )
        if rd["warnings"]:
            print("  warnings:", "; ".join(rd["warnings"]))
        return 0
    finally:
        db.close()


if __name__ == "__main__":
    raise SystemExit(main())
