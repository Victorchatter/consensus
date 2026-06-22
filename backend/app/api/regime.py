from __future__ import annotations

from typing import List
from fastapi import APIRouter, Depends, Query
from sqlalchemy.orm import Session

from app.core.database import get_db
from app import models
from app.ml.regime import detect_regime, RegimeResult

router = APIRouter(prefix="/regime", tags=["regime"])


@router.get("/detect/{asset_id}")
def detect_asset_regime(
    asset_id: int,
    window: int = Query(20, ge=5, le=100),
    db: Session = Depends(get_db),
):
    bars = (
        db.query(models.PriceBar)
        .filter(models.PriceBar.asset_id == asset_id, models.PriceBar.timeframe == "1d")
        .order_by(models.PriceBar.timestamp.asc())
        .all()
    )

    if len(bars) < window + 1:
        return {"error": f"Need at least {window + 1} daily bars, found {len(bars)}. Load history first."}

    closes = [b.close for b in bars]
    dates = [b.timestamp.strftime("%Y-%m-%d") for b in bars]

    result = detect_regime(closes, window)
    if result:
        result.date = dates[-1]
        return {
            "asset_id": asset_id,
            "latest_date": result.date,
            "regime": result.regime_label,
            "volatility_regime": result.volatility_regime,
            "trend_strength": round(result.trend_strength, 6),
            "confidence": round(result.confidence, 4),
            "features": {k: round(v, 6) for k, v in result.features.items()},
        }
    return {"error": "Could not compute regime"}


@router.get("/history/{asset_id}")
def regime_history(
    asset_id: int,
    window: int = Query(20, ge=5, le=100),
    limit: int = Query(100, ge=10, le=1000),
    db: Session = Depends(get_db),
):
    bars = (
        db.query(models.PriceBar)
        .filter(models.PriceBar.asset_id == asset_id, models.PriceBar.timeframe == "1d")
        .order_by(models.PriceBar.timestamp.asc())
        .all()
    )

    if len(bars) < window + 1:
        return {"error": f"Need at least {window + 1} daily bars, found {len(bars)}."}

    closes = [b.close for b in bars]
    dates = [b.timestamp.strftime("%Y-%m-%d") for b in bars]

    results: List[RegimeResult] = []
    for i in range(window, len(bars)):
        r = detect_regime(closes[:i + 1], window)
        if r:
            r.date = dates[i]
            results.append(r)

    # Take last N
    results = results[-limit:]

    return {
        "asset_id": asset_id,
        "window": window,
        "history": [
            {
                "date": r.date,
                "regime": r.regime_label,
                "volatility": r.volatility_regime,
                "trend_strength": round(r.trend_strength, 6),
                "confidence": round(r.confidence, 4),
            }
            for r in results
        ],
    }
