from __future__ import annotations

from typing import Optional
from fastapi import APIRouter, Depends, Query
from sqlalchemy.orm import Session

from app.core.database import get_db
from app import models
from app.journal.analytics import compute_performance, TradeSummary, PerformanceReport

router = APIRouter(prefix="/performance", tags=["performance"])


@router.get("/summary")
def performance_summary(
    start_date: Optional[str] = Query(None),
    end_date: Optional[str] = Query(None),
    strategy_id: Optional[int] = Query(None),
    db: Session = Depends(get_db),
):
    q = db.query(models.Trade).filter(models.Trade.status == "closed")
    if start_date:
        q = q.filter(models.Trade.entry_time >= start_date)
    if end_date:
        q = q.filter(models.Trade.entry_time <= end_date)
    if strategy_id:
        q = q.filter(models.Trade.strategy_id == strategy_id)

    trades = q.all()
    if not trades:
        return {"message": "No closed trades found", "report": None}

    summaries = [
        TradeSummary(
            entry_price=t.entry_price,
            exit_price=t.exit_price or t.entry_price,
            pnl=t.pnl or 0.0,
            pnl_pct=t.pnl_pct or 0.0,
            holding_bars=1,  # Simplified
        )
        for t in trades
    ]

    report = compute_performance(summaries)
    return {
        "filters": {"start_date": start_date, "end_date": end_date, "strategy_id": strategy_id},
        "report": report,
    }
