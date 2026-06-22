from __future__ import annotations

from typing import List
from fastapi import APIRouter, Depends, Query
from sqlalchemy.orm import Session

from app.core.database import get_db
from app.data.indicators import sma, ema, rsi, bollinger, macd
from app.data.feeders import OHLCVBar
from app import models

router = APIRouter(prefix="/assets", tags=["indicators"])


def _db_bars_to_ohlcv(bars: List[models.PriceBar]) -> List[OHLCVBar]:
    return [
        OHLCVBar(
            timestamp=b.timestamp,
            open_=b.open,
            high=b.high,
            low=b.low,
            close=b.close,
            volume=b.volume,
        )
        for b in bars
    ]


@router.get("/{asset_id}/indicators")
def get_indicators(
    asset_id: int,
    indicator: str = Query(..., pattern="^(sma|ema|rsi|bollinger|macd)$"),
    period: int = Query(20, ge=2, le=500),
    timeframe: str = Query("1d"),
    limit: int = Query(500, ge=50, le=5000),
    db: Session = Depends(get_db),
):
    bars = (
        db.query(models.PriceBar)
        .filter(
            models.PriceBar.asset_id == asset_id,
            models.PriceBar.timeframe == timeframe,
        )
        .order_by(models.PriceBar.timestamp.asc())
        .limit(limit)
        .all()
    )

    ohlcv = _db_bars_to_ohlcv(bars)

    if indicator == "sma":
        return {"indicator": "sma", "period": period, "values": sma(ohlcv, period)}
    elif indicator == "ema":
        return {"indicator": "ema", "period": period, "values": ema(ohlcv, period)}
    elif indicator == "rsi":
        return {"indicator": "rsi", "period": period, "values": rsi(ohlcv, period)}
    elif indicator == "bollinger":
        return {"indicator": "bollinger", "period": period, "values": bollinger(ohlcv, period)}
    elif indicator == "macd":
        return {"indicator": "macd", "values": macd(ohlcv)}

    return {"error": "Unknown indicator"}
