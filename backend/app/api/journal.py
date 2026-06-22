from __future__ import annotations

import datetime as dt
from typing import List, Optional
from fastapi import APIRouter, Depends, Query
from sqlalchemy.orm import Session

from app.core.database import get_db
from app import models, schemas

router = APIRouter(prefix="/journal", tags=["journal"])


@router.get("/entries", response_model=List[schemas.JournalEntryRead])
def list_entries(
    trade_id: Optional[int] = Query(None),
    entry_type: Optional[str] = Query(None),
    mood: Optional[str] = Query(None),
    start_date: Optional[dt.date] = Query(None),
    end_date: Optional[dt.date] = Query(None),
    search: Optional[str] = Query(None),
    limit: int = Query(100, ge=1, le=1000),
    db: Session = Depends(get_db),
):
    q = db.query(models.JournalEntry)
    if trade_id:
        q = q.filter(models.JournalEntry.trade_id == trade_id)
    if entry_type:
        q = q.filter(models.JournalEntry.entry_type == entry_type)
    if mood:
        q = q.filter(models.JournalEntry.mood == mood)
    if start_date:
        q = q.filter(models.JournalEntry.created_at >= start_date)
    if end_date:
        q = q.filter(models.JournalEntry.created_at < end_date + dt.timedelta(days=1))
    if search:
        q = q.filter(models.JournalEntry.content.ilike(f"%{search}%"))
    return q.order_by(models.JournalEntry.created_at.desc()).limit(limit).all()


@router.get("/entries/{entry_id}", response_model=schemas.JournalEntryRead)
def get_entry(entry_id: int, db: Session = Depends(get_db)):
    entry = db.query(models.JournalEntry).filter(models.JournalEntry.id == entry_id).first()
    if not entry:
        raise ValueError("Journal entry not found")
    return entry


@router.post("/entries", response_model=schemas.JournalEntryRead)
def create_entry(payload: schemas.JournalEntryCreate, db: Session = Depends(get_db)):
    entry = models.JournalEntry(**payload.model_dump())
    db.add(entry)
    db.commit()
    db.refresh(entry)
    return entry


@router.patch("/entries/{entry_id}", response_model=schemas.JournalEntryRead)
def update_entry(entry_id: int, payload: schemas.JournalEntryUpdate, db: Session = Depends(get_db)):
    entry = db.query(models.JournalEntry).filter(models.JournalEntry.id == entry_id).first()
    if not entry:
        raise ValueError("Journal entry not found")
    for field, value in payload.model_dump(exclude_unset=True).items():
        setattr(entry, field, value)
    db.commit()
    db.refresh(entry)
    return entry


@router.delete("/entries/{entry_id}")
def delete_entry(entry_id: int, db: Session = Depends(get_db)):
    entry = db.query(models.JournalEntry).filter(models.JournalEntry.id == entry_id).first()
    if not entry:
        raise ValueError("Journal entry not found")
    db.delete(entry)
    db.commit()
    return {"deleted": True}


@router.get("/performance", response_model=schemas.PerformanceSummary)
def get_performance(
    start_date: Optional[str] = Query(None),
    end_date: Optional[str] = Query(None),
    db: Session = Depends(get_db),
):
    q = db.query(models.Trade).filter(models.Trade.status == "closed")
    if start_date:
        q = q.filter(models.Trade.entry_time >= start_date)
    if end_date:
        q = q.filter(models.Trade.entry_time <= end_date)

    trades = q.all()
    total = len(trades)
    wins = [t for t in trades if (t.pnl or 0) > 0]
    losses = [t for t in trades if (t.pnl or 0) <= 0]
    win_count = len(wins)
    loss_count = len(losses)

    gross_profit = sum(t.pnl for t in wins) if wins else 0.0
    gross_loss = abs(sum(t.pnl for t in losses)) if losses else 0.0

    pnls = [t.pnl for t in trades if t.pnl is not None]
    return schemas.PerformanceSummary(
        total_trades=total,
        win_count=win_count,
        loss_count=loss_count,
        win_rate=win_count / total if total else 0.0,
        profit_factor=gross_profit / gross_loss if gross_loss else 0.0,
        max_drawdown=0.0,  # computed separately
        total_pnl=sum(pnls) if pnls else 0.0,
        avg_trade_pnl=sum(pnls) / len(pnls) if pnls else 0.0,
        best_trade=max(pnls) if pnls else None,
        worst_trade=min(pnls) if pnls else None,
    )
