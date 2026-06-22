# EchoTrader

A local-first algorithmic trading platform built with FastAPI, React, and SQLite.

## Features

- **Charts & Indicators** — Lightweight-charts v4 with SMA, EMA, Bollinger Bands, RSI, MACD, and volume.
- **Trading Journal** — Markdown entries, mood tracking, trade linking, and a monthly calendar heatmap.
- **Strategy Engine** — Rule-based and custom strategies with event-driven backtesting (slippage + commission).
- **Backtest Optimization** — Grid search, walk-forward analysis, and regime-aware parameter switching.
- **Paper Trading Bots** — Async bot loops with risk guards (max daily loss, max position size).
- **AI Agent Swarm** — News Prodigy (RSS sentiment), Financial Market Analyst (technical bias), and scheduled agents.
- **Broker Integrations** — Alpaca, Binance, OANDA, Interactive Brokers with Fernet-encrypted API keys.

## Quick Start

### Backend

```bash
cd backend
python -m venv venv
venv\Scripts\activate  # Windows
pip install -r requirements.txt
uvicorn app.main:app --reload --port 8000
```

### Frontend

```bash
cd frontend
npm install
npm run dev
```

## Project Structure

```
echotrader/
├── backend/
│   ├── app/
│   │   ├── api/          # FastAPI routers
│   │   ├── agents/       # AI agent swarm
│   │   ├── backtest/     # Event-driven backtest engine
│   │   ├── bots/         # Paper trading bot engine
│   │   ├── core/         # Encryption, config, security
│   │   ├── data/         # Indicators, bar storage
│   │   ├── models/       # SQLAlchemy models
│   │   ├── strategies/   # Built-in + custom strategies
│   │   └── main.py       # App entrypoint + lifespan
│   └── tests/
├── frontend/
│   ├── src/
│   │   ├── components/   # Shared UI components
│   │   ├── pages/        # Route-level pages
│   │   └── services/     # API wrappers
│   └── src/__tests__/
└── README.md
```

## Tech Stack

- **Backend:** Python 3.14, FastAPI, SQLAlchemy, SQLite, cryptography
- **Frontend:** React 18, TypeScript, Tailwind CSS, Vite, FullCalendar
- **Charts:** TradingView Lightweight Charts v4.1.0
- **Agents:** Pure-Python rule-based + RSS sentiment (no pandas-ta, no torch)

## Security

- API keys encrypted at rest with Fernet (PBKDF2HMAC, SHA256, 480k iterations)
- Master password optional; plain-text storage shows a warning
- No external key transmission — all broker calls originate from your machine
- Markdown preview sanitized against XSS (`escapeHtml` + `sanitizeUrl`)
- XML DOCTYPE stripping before RSS parsing to mitigate XXE

## Testing

```bash
# Backend
cd backend
python -m pytest tests/ -v

# Frontend
cd frontend
npm test -- --watchAll=false
```

## License

MIT
