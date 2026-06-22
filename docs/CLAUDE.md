# EchoTrader — Local Algorithmic Trading Platform

## Architecture

**FastAPI (Python) backend + React/Vite (TypeScript) frontend + SQLite database**

Runs entirely on localhost. No cloud dependency for core trading operations.

```
Backend  : http://localhost:8000  (Uvicorn + FastAPI)
Frontend : http://localhost:5173  (Vite dev server)
Database : SQLite file at database/echotrader.db
```

## Core Modules

| Module | Path | Purpose |
|--------|------|---------|
| Market Data | `backend/app/data/` | Real-time + historical price ingestion (Alpaca, Binance, Yahoo) |
| Strategies | `backend/app/strategies/` | Strategy base class + built-in implementations |
| Backtest | `backend/app/backtest/` | Event-driven simulation engine |
| Execution | `backend/app/execution/` | Paper + live order routing |
| Journal | `backend/app/journal/` | Trade logging + performance analytics |
| ML | `backend/app/ml/` | Regime detection, parameter optimization, regret analysis |

## Key Files

- `backend/main.py` — Uvicorn entry point, mounts all routers + WebSocket
- `backend/app/core/config.py` — Pydantic settings from `.env`
- `backend/app/models/` — SQLAlchemy ORM models
- `frontend/src/pages/` — Dashboard, ChartPage, JournalPage, CalendarPage, StrategyPage
- `frontend/src/services/api.ts` — Axios client + WebSocket hook

## Tech Stack

**Backend**
- FastAPI, Uvicorn, SQLAlchemy 2.0, Pydantic v2
- Alembic (migrations), python-dotenv, aiohttp, websockets
- Alpaca-py, CCXT, yfinance, numpy, pandas, ta-lib (or pandas-ta)
- scikit-learn, optuna (ML + optimization)

**Frontend**
- React 18, Vite, TypeScript, Tailwind CSS
- Lightweight Charts (TradingView) for charting
- FullCalendar for trade calendar
- shadcn/ui components (Radix + Tailwind)
- React Router, Axios, Zustand (state management)

**Data**
- SQLite via SQLAlchemy (local-first)
- Optional Supabase sync for cloud backup (future)

## Environment Variables

Create `.env` in `backend/`:

```
# Database
DATABASE_URL=sqlite:///./database/echotrader.db

# Alpaca (stocks/ETFs) — get from alpaca.markets
ALPACA_API_KEY=your_key
ALPACA_SECRET_KEY=your_secret
ALPACA_PAPER=true

# Binance (crypto) — get from binance.com
BINANCE_API_KEY=your_key
BINANCE_SECRET_KEY=your_secret
BINANCE_TESTNET=true

# Logging
LOG_LEVEL=INFO
```

## Running Locally

```bash
# Terminal 1 — Backend
cd echotrader/backend
python -m venv venv
source venv/bin/activate  # Windows: venv\Scripts\activate
pip install -r requirements.txt
uvicorn main:app --reload --port 8000

# Terminal 2 — Frontend
cd echotrader/frontend
npm install
npm run dev
```

Open http://localhost:5173 in browser. Backend API docs at http://localhost:8000/docs.

## Design Decisions

1. **FastAPI over Next.js API routes** — WebSocket market data requires persistent async connections; FastAPI handles this natively.
2. **SQLite over PostgreSQL** — Zero-config, file-based, portable. Can migrate to Postgres later.
3. **React/Vite over Next.js** — Lighter bundle, faster HMR, no SSR needed for a local tool.
4. **Lightweight Charts over D3/Plotly** — Purpose-built for financial time series, free, excellent performance.
5. **Paper trading default** — Every execution module checks paper flag before routing to live broker.

## Safety Rules

- API keys are backend-only. Frontend never reads or displays keys.
- `.env` is gitignored. Keys stored encrypted at rest (future batch).
- Live trading toggle requires explicit confirmation and risk disclaimer.
- All backtests include disclaimers: past performance ≠ future results.
