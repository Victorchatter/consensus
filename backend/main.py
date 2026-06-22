from __future__ import annotations

import sys
import traceback
from contextlib import asynccontextmanager

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware

from app.core.database import engine, Base
from app.core.config import settings
from app.api import (
    assets_router,
    trades_router,
    journal_router,
    strategies_router,
    backtest_router,
)

# Optional heavy imports — lazy to avoid startup crash if packages are missing
ws_router = None
data_loader_router = None
indicators_router = None
manager = None
run_seed = None

_import_errors: list[str] = []

try:
    from app.api.ws import router as ws_router
except Exception as e:
    _import_errors.append(f"ws_router: {e}")
    print(f"[IMPORT ERROR] ws_router failed: {e}")
    traceback.print_exc()
    ws_router = None

try:
    from app.api.data_loader import router as data_loader_router
except Exception as e:
    _import_errors.append(f"data_loader_router: {e}")
    print(f"[IMPORT ERROR] data_loader_router failed: {e}")
    traceback.print_exc()
    data_loader_router = None

try:
    from app.api.indicators import router as indicators_router
except Exception as e:
    _import_errors.append(f"indicators_router: {e}")
    print(f"[IMPORT ERROR] indicators_router failed: {e}")
    traceback.print_exc()
    indicators_router = None

try:
    from app.data.seed import run_seed
except Exception as e:
    _import_errors.append(f"run_seed: {e}")
    print(f"[IMPORT ERROR] run_seed failed: {e}")
    traceback.print_exc()
    run_seed = None

try:
    from app.data.ws_manager import manager
except Exception as e:
    _import_errors.append(f"ws_manager: {e}")
    print(f"[IMPORT ERROR] ws_manager failed: {e}")
    traceback.print_exc()
    manager = None

try:
    from app.agents.scheduler import scheduler as agent_scheduler
except Exception as e:
    _import_errors.append(f"agent_scheduler: {e}")
    print(f"[IMPORT ERROR] agent_scheduler failed: {e}")
    traceback.print_exc()
    agent_scheduler = None

# Quote poller — lightweight fallback when Alpaca WS is unavailable
quote_poller = None
try:
    from app.data.quote_poller import QuotePoller
    quote_poller = QuotePoller(interval_sec=30)
except Exception as e:
    _import_errors.append(f"quote_poller: {e}")
    print(f"[IMPORT ERROR] quote_poller failed: {e}")
    traceback.print_exc()


@asynccontextmanager
async def lifespan(app: FastAPI):
    print(f"[STARTUP] Database URL: {settings.database_url}")
    try:
        Base.metadata.create_all(bind=engine)
        print("[STARTUP] Database tables created successfully.")
    except Exception as e:
        print(f"[STARTUP ERROR] Failed to create tables: {e}")
        traceback.print_exc()

    if run_seed:
        try:
            run_seed()
            print("[STARTUP] Database seeded successfully.")
        except Exception as e:
            print(f"[STARTUP ERROR] Failed to seed database: {e}")
            traceback.print_exc()
    else:
        print("[STARTUP WARNING] Seed function unavailable.")

    if manager:
        import asyncio
        asyncio.create_task(manager.start())

    if agent_scheduler:
        try:
            await agent_scheduler.start()
            print("[STARTUP] Agent scheduler started.")
        except Exception as e:
            print(f"[STARTUP ERROR] Agent scheduler failed to start: {e}")
            traceback.print_exc()

    if quote_poller:
        try:
            await quote_poller.start()
            print("[STARTUP] Quote poller started.")
        except Exception as e:
            print(f"[STARTUP ERROR] Quote poller failed to start: {e}")
            traceback.print_exc()

    if _import_errors:
        print(f"[STARTUP WARNING] {len(_import_errors)} optional module(s) failed to import.")
        for err in _import_errors:
            print(f"  - {err}")

    yield

    if manager:
        await manager.stop()
    if quote_poller:
        await quote_poller.stop()
    if agent_scheduler:
        await agent_scheduler.stop()


app = FastAPI(
    title="EchoTrader API",
    version="0.1.0",
    lifespan=lifespan,
)

app.add_middleware(
    CORSMiddleware,
    allow_origins=[
        "http://localhost:5173",
        "http://127.0.0.1:5173",
        "http://localhost:5174",
        "http://127.0.0.1:5174",
        "http://localhost:5175",
        "http://127.0.0.1:5175",
    ],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# ── ROUTERS ────────────────────────────────────────────────────

app.include_router(assets_router)
app.include_router(trades_router)
app.include_router(journal_router)
app.include_router(strategies_router)
app.include_router(backtest_router)

if data_loader_router:
    app.include_router(data_loader_router)
if indicators_router:
    app.include_router(indicators_router)
if ws_router:
    app.include_router(ws_router)

try:
    from app.api.regime import router as regime_router
    app.include_router(regime_router)
except Exception as e:
    print(f"[IMPORT ERROR] regime_router failed: {e}")
    traceback.print_exc()

try:
    from app.api.performance import router as performance_router
    app.include_router(performance_router)
except Exception as e:
    print(f"[IMPORT ERROR] performance_router failed: {e}")
    traceback.print_exc()

try:
    from app.api.execution import router as execution_router
    app.include_router(execution_router)
except Exception as e:
    print(f"[IMPORT ERROR] execution_router failed: {e}")
    traceback.print_exc()

try:
    from app.api.bots import router as bots_router
    app.include_router(bots_router)
except Exception as e:
    print(f"[IMPORT ERROR] bots_router failed: {e}")
    traceback.print_exc()

try:
    from app.api.calendar import router as calendar_router
    app.include_router(calendar_router)
except Exception as e:
    print(f"[IMPORT ERROR] calendar_router failed: {e}")
    traceback.print_exc()

try:
    from app.api.agents import router as agents_router
    app.include_router(agents_router)
except Exception as e:
    print(f"[IMPORT ERROR] agents_router failed: {e}")
    traceback.print_exc()

try:
    from app.api.brokers import router as brokers_router
    app.include_router(brokers_router)
except Exception as e:
    print(f"[IMPORT ERROR] brokers_router failed: {e}")
    traceback.print_exc()


@app.get("/")
def root():
    return {
        "service": "EchoTrader API",
        "version": "0.1.0",
        "docs": "/docs",
        "health": "/health",
    }


@app.get("/health")
def health_check():
    db_info = {}
    try:
        from app.core.database import SessionLocal
        from app import models
        db = SessionLocal()
        db_info = {
            "assets": db.query(models.Asset).count(),
            "strategies": db.query(models.Strategy).count(),
            "backtests": db.query(models.BacktestRun).count(),
            "trades": db.query(models.Trade).count(),
            "price_bars": db.query(models.PriceBar).count(),
            "agent_reports": db.query(models.AgentReport).count(),
            "news_signals": db.query(models.NewsSignal).count(),
        }
        db.close()
    except Exception as e:
        db_info = {"error": str(e)}

    return {
        "status": "ok",
        "service": "echotrader-api",
        "database_url": settings.database_url,
        "database": db_info,
        "missing_modules": _import_errors,
    }
