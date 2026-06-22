from __future__ import annotations

import datetime as dt
from typing import Optional
from fastapi import APIRouter, Depends, BackgroundTasks
from sqlalchemy.orm import Session

from app.core.database import get_db
from app.data.feeders import get_feeder_for_source
from app import models

router = APIRouter(prefix="/assets", tags=["data-loader"])


@router.post("/{asset_id}/load-history")
def load_asset_history(
    asset_id: int,
    start: Optional[dt.date] = None,
    end: Optional[dt.date] = None,
    timeframe: str = "1d",
    db: Session = Depends(get_db),
):
    asset = db.query(models.Asset).filter(models.Asset.id == asset_id).first()
    if not asset:
        return {"error": "Asset not found"}

    if end is None:
        end = dt.date.today()
    if start is None:
        start = end - dt.timedelta(days=365 * 2)

    feeder = get_feeder_for_source(asset.data_source or "yahoo")
    bars = feeder.fetch_historical(asset.symbol, start, end, timeframe)

    inserted = 0
    for bar in bars:
        existing = (
            db.query(models.PriceBar)
            .filter(
                models.PriceBar.asset_id == asset_id,
                models.PriceBar.timestamp == bar.timestamp,
                models.PriceBar.timeframe == timeframe,
            )
            .first()
        )
        if existing:
            # Update existing bar
            existing.open = bar.open
            existing.high = bar.high
            existing.low = bar.low
            existing.close = bar.close
            existing.volume = bar.volume
        else:
            db.add(
                models.PriceBar(
                    asset_id=asset_id,
                    timestamp=bar.timestamp,
                    timeframe=timeframe,
                    open=bar.open,
                    high=bar.high,
                    low=bar.low,
                    close=bar.close,
                    volume=bar.volume,
                )
            )
            inserted += 1

    db.commit()
    return {
        "asset_id": asset_id,
        "symbol": asset.symbol,
        "timeframe": timeframe,
        "start": start.isoformat(),
        "end": end.isoformat(),
        "bars_fetched": len(bars),
        "bars_inserted": inserted,
    }
