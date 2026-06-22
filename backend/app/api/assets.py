from __future__ import annotations

from typing import List, Optional
from fastapi import APIRouter, Depends, Query
from sqlalchemy.orm import Session

from app.core.database import get_db
from app import models, schemas

router = APIRouter(prefix="/assets", tags=["assets"])


@router.get("", response_model=List[schemas.AssetRead])
def list_assets(
    asset_class: Optional[str] = Query(None),
    exchange: Optional[str] = Query(None),
    search: Optional[str] = Query(None),
    db: Session = Depends(get_db),
):
    q = db.query(models.Asset).filter(models.Asset.is_active == True)
    if asset_class:
        q = q.filter(models.Asset.asset_class == asset_class)
    if exchange:
        q = q.filter(models.Asset.exchange == exchange)
    if search:
        q = q.filter(
            (models.Asset.symbol.ilike(f"%{search}%"))
            | (models.Asset.name.ilike(f"%{search}%"))
        )
    return q.all()


@router.post("", response_model=schemas.AssetRead)
def create_asset(payload: schemas.AssetCreate, db: Session = Depends(get_db)):
    asset = models.Asset(**payload.model_dump())
    db.add(asset)
    db.commit()
    db.refresh(asset)
    return asset


@router.get("/{asset_id}", response_model=schemas.AssetRead)
def get_asset(asset_id: int, db: Session = Depends(get_db)):
    return db.query(models.Asset).filter(models.Asset.id == asset_id).first()


@router.get("/{asset_id}/bars", response_model=List[schemas.PriceBarRead])
def get_bars(
    asset_id: int,
    timeframe: str = Query("1d"),
    limit: int = Query(500, ge=1, le=5000),
    db: Session = Depends(get_db),
):
    bars = (
        db.query(models.PriceBar)
        .filter(models.PriceBar.asset_id == asset_id, models.PriceBar.timeframe == timeframe)
        .order_by(models.PriceBar.timestamp.desc())
        .limit(limit)
        .all()
    )
    return list(reversed(bars))


@router.get("/{asset_id}/quote", response_model=Optional[schemas.QuoteRead])
def get_latest_quote(asset_id: int, db: Session = Depends(get_db)):
    return (
        db.query(models.Quote)
        .filter(models.Quote.asset_id == asset_id)
        .order_by(models.Quote.timestamp.desc())
        .first()
    )
