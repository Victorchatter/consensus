from __future__ import annotations

import threading
from typing import List, Optional
from fastapi import APIRouter, Depends, Query
from sqlalchemy.orm import Session

from app.core.database import get_db
from app import models
from app.agents.media_sources import get_feeds, add_feed, remove_feed

router = APIRouter(prefix="/agents", tags=["agents"])


def _run_agent_in_thread(agent_type: str):
    """Fire-and-forget agent execution in a daemon thread."""
    print(f"[ManualTrigger] === THREAD START === agent={agent_type}")
    try:
        if agent_type == "news_prodigy":
            from app.agents.news_prodigy import NewsProdigy
            NewsProdigy().run()
        elif agent_type == "financial_analyst":
            from app.agents.financial_analyst import FinancialMarketAnalyst
            FinancialMarketAnalyst().run()
        elif agent_type == "economic_analyst":
            from app.agents.economic_analyst import EconomicAnalyst
            EconomicAnalyst().run()
        elif agent_type == "political_analyst":
            from app.agents.political_analyst import PoliticalAnalyst
            PoliticalAnalyst().run()
        elif agent_type == "ceo_agent":
            from app.agents.ceo_agent import CEOAgent
            CEOAgent().run()
        else:
            print(f"[ManualTrigger] Unknown agent type: {agent_type}")
    except Exception as e:
        print(f"[ManualTrigger] Agent {agent_type} FAILED: {e}")
        import traceback
        traceback.print_exc()
    finally:
        print(f"[ManualTrigger] === THREAD END === agent={agent_type}")


@router.get("/reports")
def list_reports(
    agent_type: Optional[str] = Query(None),
    limit: int = Query(50, ge=1, le=200),
    db: Session = Depends(get_db),
):
    q = db.query(models.AgentReport)
    if agent_type:
        q = q.filter(models.AgentReport.agent_type == agent_type)
    return q.order_by(models.AgentReport.timestamp.desc()).limit(limit).all()


@router.get("/signals")
def list_signals(
    agent_type: Optional[str] = Query(None),
    symbol: Optional[str] = Query(None),
    active_only: bool = Query(True),
    limit: int = Query(100, ge=1, le=500),
    db: Session = Depends(get_db),
):
    q = db.query(models.AgentSignal)
    if agent_type:
        q = q.filter(models.AgentSignal.agent_type == agent_type)
    if symbol:
        q = q.filter(models.AgentSignal.symbol == symbol)
    if active_only:
        q = q.filter(
            (models.AgentSignal.expires_at == None) |
            (models.AgentSignal.expires_at >= __import__("datetime").datetime.utcnow())
        )
    return q.order_by(models.AgentSignal.created_at.desc()).limit(limit).all()


@router.get("/news")
def list_news_signals(
    symbol: Optional[str] = Query(None),
    severity: Optional[str] = Query(None),
    limit: int = Query(50, ge=1, le=200),
    db: Session = Depends(get_db),
):
    q = db.query(models.NewsSignal)
    if symbol:
        q = q.filter(models.NewsSignal.symbol == symbol)
    if severity:
        q = q.filter(models.NewsSignal.severity == severity)
    return q.order_by(models.NewsSignal.timestamp.desc()).limit(limit).all()


@router.get("/macro")
def get_macro_regimes(
    limit: int = Query(30, ge=1, le=100),
    db: Session = Depends(get_db),
):
    return db.query(models.MarketRegime).order_by(models.MarketRegime.date.desc()).limit(limit).all()


@router.post("/run/{agent_type}")
def run_agent_now(agent_type: str):
    """Manually trigger an agent or the full council in a background thread."""
    t = threading.Thread(target=_run_agent_in_thread, args=(agent_type,), daemon=True)
    t.start()
    return {"triggered": True, "agent_type": agent_type, "message": "Agent started in background thread"}


@router.get("/council/latest")
def get_council_latest(db: Session = Depends(get_db)):
    """Return the most recent CEO decision (legacy name preserved for frontend compat)."""
    report = (
        db.query(models.AgentReport)
        .filter(models.AgentReport.agent_type == "ceo_agent")
        .order_by(models.AgentReport.timestamp.desc())
        .first()
    )
    if not report:
        return {"error": "No CEO decisions yet"}
    return {
        "timestamp": report.timestamp,
        "summary": report.summary,
        "bias_score": report.bias_score,
        "confidence": report.confidence,
        "raw_data_json": report.raw_data_json,
    }


# ── MEDIA SOURCE CONFIG ───────────────────────────────────────

class _FeedPayload:
    def __init__(self, url: str):
        self.url = url


@router.get("/feeds")
def list_feeds():
    """Return the current list of RSS feed URLs used by NewsProdigy."""
    return {"feeds": get_feeds()}


@router.post("/feeds")
def create_feed(payload: dict):
    """Add a new RSS feed URL."""
    url = payload.get("url", "").strip()
    if not url:
        return {"error": "URL is required"}, 400
    feeds = add_feed(url)
    return {"feeds": feeds, "added": url}


@router.delete("/feeds")
def delete_feed(payload: dict):
    """Remove an RSS feed URL."""
    url = payload.get("url", "").strip()
    if not url:
        return {"error": "URL is required"}, 400
    feeds = remove_feed(url)
    return {"feeds": feeds, "removed": url}
