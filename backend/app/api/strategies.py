from __future__ import annotations

from typing import List
from fastapi import APIRouter, Depends
from sqlalchemy.orm import Session

from app.core.database import get_db
from app import models, schemas

router = APIRouter(prefix="/strategies", tags=["strategies"])


@router.get("", response_model=List[schemas.StrategyRead])
def list_strategies(db: Session = Depends(get_db)):
    return db.query(models.Strategy).filter(models.Strategy.is_active == True).all()


@router.post("", response_model=schemas.StrategyRead)
def create_strategy(payload: schemas.StrategyCreate, db: Session = Depends(get_db)):
    strategy = models.Strategy(**payload.model_dump())
    db.add(strategy)
    db.commit()
    db.refresh(strategy)
    return strategy


@router.get("/{strategy_id}", response_model=schemas.StrategyRead)
def get_strategy(strategy_id: int, db: Session = Depends(get_db)):
    return db.query(models.Strategy).filter(models.Strategy.id == strategy_id).first()
