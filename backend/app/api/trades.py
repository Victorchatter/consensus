from __future__ import annotations

import datetime as dt
from typing import List, Optional
from fastapi import APIRouter, Depends, Query
from sqlalchemy.orm import Session

from app.core.database import get_db
from app import models, schemas

router = APIRouter(prefix="/trades", tags=["trades"])


@router.get("", response_model=List[schemas.TradeRead])
def list_trades(
    status: Optional[str] = Query(None),
    asset_id: Optional[int] = Query(None),
    strategy_id: Optional[int] = Query(None),
    start_date: Optional[dt.date] = Query(None),
    end_date: Optional[dt.date] = Query(None),
    is_paper: Optional[bool] = Query(None),
    db: Session = Depends(get_db),
):
    q = db.query(models.Trade)
    if status:
        q = q.filter(models.Trade.status == status)
    if asset_id:
        q = q.filter(models.Trade.asset_id == asset_id)
    if strategy_id:
        q = q.filter(models.Trade.strategy_id == strategy_id)
    if start_date:
        q = q.filter(models.Trade.entry_time >= start_date)
    if end_date:
        q = q.filter(models.Trade.entry_time <= end_date)
    if is_paper is not None:
        q = q.filter(models.Trade.is_paper == is_paper)
    return q.order_by(models.Trade.entry_time.desc()).all()


@router.post("", response_model=schemas.TradeRead)
def create_trade(payload: schemas.TradeCreate, db: Session = Depends(get_db)):
    trade = models.Trade(
        **payload.model_dump(),
        entry_time=dt.datetime.utcnow(),
    )
    db.add(trade)
    db.commit()
    db.refresh(trade)
    return trade


@router.patch("/{trade_id}", response_model=schemas.TradeRead)
def update_trade(trade_id: int, payload: schemas.TradeUpdate, db: Session = Depends(get_db)):
    trade = db.query(models.Trade).filter(models.Trade.id == trade_id).first()
    if not trade:
        raise ValueError("Trade not found")
    for field, value in payload.model_dump(exclude_unset=True).items():
        setattr(trade, field, value)
    db.commit()
    db.refresh(trade)
    return trade


@router.get("/{trade_id}", response_model=schemas.TradeRead)
def get_trade(trade_id: int, db: Session = Depends(get_db)):
    return db.query(models.Trade).filter(models.Trade.id == trade_id).first()
