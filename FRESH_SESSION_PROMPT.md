# EchoTrader — Fresh Claude Code Session Prompt

> **Date:** 2026-06-05  
> **Project:** EchoTrader — Local-first algorithmic trading platform (FastAPI + React + SQLite + TradingView Lightweight Charts)  
> **Repository context:** Backend at `echotrader/backend/`, Frontend at `echotrader/frontend/`, Database at `echotrader/database/echotrader.db`

---

## Project Overview

EchoTrader is a professional-grade, **local-first algorithmic trading platform** that runs entirely on the user's Windows machine. It is designed to go from paper trading to live execution without relying on cloud services or paid subscriptions to start.

**Stack:**
- **Backend:** FastAPI (Python), SQLite, pure-Python analytics (no compiled ML libs due to Python 3.14 incompatibility).
- **Frontend:** React 18 + Vite + TypeScript + Tailwind CSS + TradingView Lightweight Charts.
- **Data:** Alpaca (US stocks), CCXT/Binance (crypto), Yahoo Finance (historical fallback).
- **Deployment:** Localhost only; Windows PowerShell startup script (`start.ps1`).

---

## 🔴 CRITICAL — Priority 1: Asset Charts Do Not Load

**Problem:** On the Chart page (`/chart`), clicking **"Load History"** produces **nothing**. No chart renders for **any timeframe** (1m, 5m, 15m, 1h, 1d). The page appears completely blank where the TradingView Lightweight Chart should be.

**What has been tried:**
- ChartPage was previously rewritten with RSI sync via `subscribeVisibleLogicalRangeChange`
- Overlay indicators were moved to the right price scale
- Timeframe `1w` was removed
- Auto-load history logic was added

**What is needed:**
- Diagnose why `Load History` is a no-op — check the frontend `handleLoadHistory` flow, the API call to `/api/assets/{id}/history` (or equivalent), and whether the response is reaching the chart component.
- Verify the TradingView Lightweight Charts library is correctly initialized and receiving data series.
- Check browser DevTools Console and Network tabs for JavaScript errors, 404s, or empty responses.
- If the endpoint returns empty arrays, investigate whether `PriceBar` data exists in the SQLite database for the selected asset + timeframe.
- If the endpoint is slow or timing out, check whether the query is unindexed or the database is locked by another process.
- **Fix must be robust** — the chart is the core UI of the platform. Do not proceed to other features until charts load reliably across all timeframes.

**Key files to inspect:**
- `frontend/src/pages/ChartPage.tsx`
- `frontend/src/hooks/usePriceHistory.ts` (or equivalent history-fetching hook)
- `backend/app/api/assets.py` (or wherever history endpoint lives)
- `backend/app/models.py` (`PriceBar` table definition)

---

## 🔴 CRITICAL — Priority 2: Intelligence Page Produces Nothing

**Problem:** On the Intelligence page (`/intelligence`), when any bot or agent is triggered, **no reports, signals, or responses appear**. The page remains empty or shows perpetual loading states.

**Background:**
- The agent swarm consists of: `NewsProdigy`, `FinancialMarketAnalyst`, `EconomicAnalyst`, `PoliticalAnalyst`, and `CEOAgent` (sole qualitative analyzer + trade executor).
- The `CEOAgent` was designed to consume digest summaries from sub-agents and emit decisions + a paperclip-style heartbeat.
- The scheduler wraps all agent `.run()` calls in `asyncio.to_thread()` to prevent event-loop blocking.
- DuckDuckGo web searches have a circuit breaker, browser headers, 25s timeout, and silent failures.

**Suspected causes to investigate:**
1. **Agent `.run()` returns empty digests** — because DDG circuit breaker is tripped, RSS feeds are down, or search queries return no results. The agents then have nothing to store in `raw_data_json`.
2. **Database write failure** — even if agents gather data, storing `raw_data_json` may fail silently (check `json_safe()` serialization in `_utils.py`, verify no `datetime` objects leak through).
3. **Frontend not fetching results** — the IntelligencePage may not be calling the correct API endpoint, or the endpoint returns empty arrays because the `AgentReport` / `NewsSignal` tables are empty.
4. **CEO Agent logic bug** — the CEO may be failing to produce a report because sub-agent inputs are empty or its evaluation logic crashes.

**What is needed:**
- Add verbose logging inside every agent's `.run()` method so we can see: (a) whether it was invoked, (b) whether it fetched data, (c) what it tried to store.
- Verify the `AgentReport` and `NewsSignal` tables have rows by querying the database directly.
- Add a **manual trigger endpoint** (e.g., `POST /api/agents/run/{agent_name}`) so agents can be forced to run on-demand for debugging.
- Ensure the IntelligencePage displays: agent reports, news signals, CEO decisions, heartbeat messages, and recently executed trades.

**Key files to inspect:**
- `backend/app/agents/ceo_agent.py`
- `backend/app/agents/news_prodigy.py`
- `backend/app/agents/financial_analyst.py`
- `backend/app/agents/economic_analyst.py`
- `backend/app/agents/political_analyst.py`
- `backend/app/agents/scheduler.py`
- `backend/app/agents/_utils.py`
- `frontend/src/pages/IntelligencePage.tsx`
- `backend/app/models.py` (`AgentReport`, `NewsSignal`)

---

## 🟡 HIGH — Priority 3: Expand Agent Data Sources with Curated Media Feeds

**User offer:** The user can provide **links to international media sources** (news outlets, financial blogs, government data portals, etc.). These should be wired into the agents so they gather real information and forward synthesized digests to the CEO Agent for evaluation.

**What is needed:**
- Design a **configurable source list** (e.g., a Python list/dict or a small JSON config) where the user can drop URLs.
- Update `NewsProdigy` to fetch RSS/Atom feeds from these URLs instead of hardcoded defaults.
- Add a generic **web scraper** or **RSS parser** that can handle diverse site formats (fallback to raw HTML title extraction if RSS is unavailable).
- Rate-limit and cache fetches so the same source isn't hammered every 5 minutes.
- Ensure fetched articles are deduplicated by URL before storage.
- Pass article summaries to `CEOAgent` as part of its context window.

**Key files to modify:**
- `backend/app/agents/news_prodigy.py`
- `backend/app/agents/web_tools.py` (add RSS parsing helper)
- `backend/app/agents/ceo_agent.py` (consume new source data)

---

## 🟡 HIGH — Priority 4: Explain Bot Lifecycle + Build Exchange Connector

**User question:** "I can now create trading bots, but I don't understand how they run and how they will execute trades. I think I need to add a connector app, like in ChatGPT or Claude, where you can connect your exchange profile with the bot and so that it can place the trades for you. I need you to explain this to me and show me how to do it."

### 4A — Explain How Bots Currently Work

Before writing code, explain in plain English:
1. **Where is a bot stored after creation?** (`BotConfig` in SQLite → `backend/app/models.py`)
2. **What starts a bot?** (Is there a background loop? Does the user manually click "Start"? Is it event-driven?)
3. **How does a bot decide to trade?** (Does it poll price data? Does it subscribe to WebSocket ticks? Does it run on a timer?)
4. **What is "paper trading" vs "live trading" in this codebase?** (`PaperAccount` in `backend/app/execution/paper.py` vs a real exchange API)
5. **How are bot trades recorded?** (`Trade` table, `Journal` entries)
6. **What happens when a bot hits `max_hold_minutes` or `close_before_market_close`?** (Scalp guards)

Trace the exact code path from **"user clicks Create Bot"** → **"a trade appears in the journal"**. Point to specific functions and files.

### 4B — Design & Build an Exchange Connector

**Goal:** Allow the user to connect a real exchange API key (e.g., Alpaca, Binance, Interactive Brokers, or any broker with a REST API) so the bot can place live trades.

**Architecture to implement:**
1. **Exchange Connector abstraction layer**
   - `backend/app/exchanges/base.py` — abstract class `ExchangeConnector` with methods:
     - `get_account()` → balance, buying power
     - `get_quote(symbol)` → bid/ask/last
     - `place_order(symbol, side, qty, type='market', limit_price=None)` → order ID
     - `get_order_status(order_id)` → filled / partial / open
     - `cancel_order(order_id)`
   - `backend/app/exchanges/paper.py` — existing paper trading implementation, refactored to inherit from base.
   - `backend/app/exchanges/alpaca.py` (or `binance.py`, `ibkr.py`) — first real implementation.

2. **API Key management**
   - New model: `ExchangeCredential` (encrypted at rest, even if just AES with a local key for now).
   - New API endpoints:
     - `POST /api/brokers/connect` — store API key + secret + optional paper/live flag.
     - `GET /api/brokers` — list connected exchanges.
     - `DELETE /api/brokers/{id}` — disconnect.
   - **Never log raw secrets.**

3. **Bot execution mode toggle**
   - Add `mode: "paper" | "live"` to `BotConfig`.
   - When a bot runs:
     - If `mode == "paper"` → route to `PaperConnector`.
     - If `mode == "live"` → look up `ExchangeCredential` for the chosen exchange, instantiate the real connector, and route orders there.
   - **Live orders must require explicit user confirmation on first run** (safety guard).

4. **Frontend UI**
   - New page or modal: **"Connect Exchange"** — form for API key, secret, exchange selector, paper/live toggle.
   - Bot creation form: add **"Trading Mode"** dropdown (Paper / Live) and **"Exchange Account"** selector.
   - Bot status card: show `mode` badge (green = paper, red = live) and last known account balance.

**Key files to create/modify:**
- `backend/app/exchanges/__init__.py`
- `backend/app/exchanges/base.py`
- `backend/app/exchanges/paper.py`
- `backend/app/exchanges/alpaca.py` (starter real connector)
- `backend/app/models.py` (add `ExchangeCredential`)
- `backend/app/api/brokers.py` (expand)
- `backend/app/api/bots.py` (add mode + exchange_id)
- `backend/app/bots/bot.py` (route to correct connector)
- `frontend/src/pages/BotControlPage.tsx`
- `frontend/src/pages/SettingsPage.tsx` (or new `ExchangeConnectPage.tsx`)

---

## 🟢 MEDIUM — Known Fixed Issues (Do Not Regress)

These were fixed in the previous session. Ensure they remain working:

| Fix | File |
|-----|------|
| Agent scheduler uses `asyncio.to_thread()` | `backend/app/agents/scheduler.py` |
| DDG circuit breaker + headers + 25s timeout | `backend/app/agents/web_tools.py` |
| `json_safe()` helper for datetime serialization | `backend/app/agents/_utils.py` |
| `realized_pnl` added to `PaperAccount` | `backend/app/execution/paper.py` |
| Vite proxy targets `127.0.0.1:8000` | `frontend/vite.config.ts` |
| Root route `/` and `/health` with DB counts | `backend/main.py` |
| Scalp guards (`max_hold_minutes`, `close_before_market_close`) | `backend/app/bots/bot.py`, `frontend/src/pages/BotControlPage.tsx` |

---

## 🛠 Session Startup Commands

When the user asks "how do I start the app?", give these **in this exact order**:

```powershell
# 1. Kill any stale uvicorn processes on port 8000
netstat -ano | findstr :8000
taskkill /PID <PID> /F

# 2. Start backend (PowerShell)
cd C:\Users\Victor\echotrader\backend
.\venv\Scripts\Activate.ps1
uvicorn main:app --reload --port 8000

# 3. Start frontend (new PowerShell window)
cd C:\Users\Victor\echotrader\frontend
npm run dev
```

Then verify:
```powershell
curl http://127.0.0.1:8000/
curl http://127.0.0.1:8000/health
```

---

## 📝 Notes for the AI

- **Database is 13.7 MB and intact.** Data is NOT being lost on startup. `Base.metadata.create_all()` is non-destructive and `run_seed()` skips existing rows.
- **Windows 11 environment.** Use `127.0.0.1` instead of `localhost` for network addresses to avoid IPv6 resolution issues.
- **Backend must stay responsive.** Any network I/O (RSS, web search, exchange API calls) must run in `asyncio.to_thread()` or an executor, never directly on the event loop.
- **User is a solo founder.** Prefers structured batch workflow. Do not ask excessive clarifying questions — diagnose, propose, implement.
- **GitHub username:** Victorchatter. If GitHub setup comes up, the repo should be `Victorchatter/echotrader`.

---

## ✅ Definition of Done for This Session

1. [ ] Chart page loads candles + indicators on all timeframes after clicking "Load History"
2. [ ] Intelligence page shows agent reports, news signals, and CEO heartbeat when agents run
3. [ ] Agents can fetch from user-provided international media source URLs
4. [ ] User understands bot lifecycle (creation → decision → execution → journal)
5. [ ] Exchange connector abstraction exists with at least one real implementation (Alpaca or other)
6. [ ] Frontend allows connecting an exchange API key and toggling Paper vs Live mode per bot

---

## Legacy Context (Preserved for Reference)

### What Already Exists (Do NOT Rebuild)
1. **Database Models** — Assets, PriceBars, Trades, JournalEntries, Strategies, BacktestRuns, CalendarEvents, DailyPnL.
2. **Pure-Python Indicators** — SMA, EMA, RSI, Bollinger Bands, MACD in `app/data/indicators.py`.
3. **Event-Driven Backtest Engine** — Replays bars bar-by-bar, simulates fills with slippage (0.05%) and commission (0.1%).
4. **Paper Trading Engine** — Virtual balance, position tracking, risk guards.
5. **FastAPI Endpoints** — `/strategies`, `/backtest/*`, `/assets`, `/trades`, `/journal`, `/paper/*`, `/bots`, `/agents`, `/calendar`, `/brokers`.
6. **Frontend Shell** — React Router layout, sidebar navigation, dark theme.
7. **StrategyPage** — Select strategy → select asset → run backtest → view equity chart + performance metrics.
8. **WebSocket Market Data Hook** — `useMarketData.ts` with reconnection hardening.
9. **Error Boundary** — Prevents black-screen crashes.
10. **Lazy Imports** — Heavy packages imported lazily to prevent startup crashes.
11. **Windows Startup Script** — `start.ps1` creates venv, installs deps, launches backend + frontend.

### Known Legacy Issues to Keep in Mind
- **MACD Momentum strategy is BROKEN** — Every backtest run fails with `list index out of range`. Likely in `app/strategies/builtin.py`. Other strategies work fine.

### Technical Constraints (Non-Negotiable)
1. **Python 3.14.x on Windows.** No compiled packages (`numba`, `pandas-ta`, `scikit-learn`, `optuna`, `torch`).
2. **SQLite only.** No PostgreSQL, no Redis.
3. **Windows paths.** Use `Path(...).resolve()` and `.as_posix()`.
4. **Lazy imports.** Heavy packages imported inside functions.
5. **Frontend resilience.** Handle `null`/`undefined`, use Error Boundaries.
6. **No cloud dependencies for core operation.** Platform must run offline after initial setup.
