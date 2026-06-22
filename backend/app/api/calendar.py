from __future__ import annotations

import datetime as dt
from typing import List, Optional
from fastapi import APIRouter, Depends, Query
from sqlalchemy.orm import Session

from app.core.database import get_db
from app import models, schemas

router = APIRouter(prefix="/calendar", tags=["calendar"])


@router.get("/events", response_model=List[schemas.CalendarEventRead])
def list_events(
    start_date: Optional[dt.date] = Query(None),
    end_date: Optional[dt.date] = Query(None),
    event_type: Optional[str] = Query(None),
    db: Session = Depends(get_db),
):
    q = db.query(models.CalendarEvent)
    if start_date:
        q = q.filter(models.CalendarEvent.date >= start_date)
    if end_date:
        q = q.filter(models.CalendarEvent.date <= end_date)
    if event_type:
        q = q.filter(models.CalendarEvent.event_type == event_type)
    return q.order_by(models.CalendarEvent.date.desc()).all()


@router.post("/events", response_model=schemas.CalendarEventRead)
def create_event(payload: schemas.CalendarEventCreate, db: Session = Depends(get_db)):
    event = models.CalendarEvent(**payload.model_dump())
    db.add(event)
    db.commit()
    db.refresh(event)
    return event


@router.patch("/events/{event_id}", response_model=schemas.CalendarEventRead)
def update_event(event_id: int, payload: schemas.CalendarEventRead, db: Session = Depends(get_db)):
    event = db.query(models.CalendarEvent).filter(models.CalendarEvent.id == event_id).first()
    if not event:
        raise ValueError("Event not found")
    for field, value in payload.model_dump(exclude={"id"}, exclude_unset=True).items():
        setattr(event, field, value)
    db.commit()
    db.refresh(event)
    return event


@router.delete("/events/{event_id}")
def delete_event(event_id: int, db: Session = Depends(get_db)):
    event = db.query(models.CalendarEvent).filter(models.CalendarEvent.id == event_id).first()
    if not event:
        raise ValueError("Event not found")
    db.delete(event)
    db.commit()
    return {"deleted": True}


@router.get("/daily-pnl")
def get_daily_pnl(
    start_date: Optional[dt.date] = Query(None),
    end_date: Optional[dt.date] = Query(None),
    db: Session = Depends(get_db),
):
    q = db.query(models.DailyPnL)
    if start_date:
        q = q.filter(models.DailyPnL.date >= start_date)
    if end_date:
        q = q.filter(models.DailyPnL.date <= end_date)
    return q.order_by(models.DailyPnL.date.asc()).all()
