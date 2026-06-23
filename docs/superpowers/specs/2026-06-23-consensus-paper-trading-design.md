# Consensus Phase 2 — Paper Trading Design

> Status: approved 2026-06-23. Repo: github.com/Victorchatter/consensus.
> Builds on Phase 1 (backtest + data-loader). See `HANDOFF.md`.

## Goal

Run `ConsensusStrategy` continuously against real-time BTC/USDT bars through
EchoTrader's paper engine + bot loop, log per-trade vote breakdowns to SQLite
for audit, and enforce an execution-layer kill-switch / max-daily-loss /
position cap that a strategy bug cannot bypass. Live stays OFF by default.

## Hard constraints (unchanged)

Python 3.14, no compiled ML libs, SQLite only, `127.0.0.1` not `localhost`,
network I/O off the event loop, live trading OFF by default. Bars in via
`load_bars()`, writes via `store_timestamp()`.

## Decisions (locked)

- **Kill-switch:** latched on first daily-loss breach; auto-resets at UTC day
  rollover; manual `reset()` available. Blocks opening orders, allows closing.
- **Position cap:** rejects oversized *opening* orders outright (no silent shrink).
- **Persistence:** new append-only `ConsensusSignal` audit table + closed `Trade`
  rows written to the existing table.
- **Scope:** BTC/USDT only, 5m, source=binance (CCXT public OHLCV, no keys), 24/7.

## Components

### 1. `DefaultConsensusStrategy` — `app/consensus/default_strategy.py`
Zero-arg subclass so the bot's `self.strategy_class()` contract is unchanged:

```python
class DefaultConsensusStrategy(ConsensusStrategy):
    def __init__(self):
        super().__init__(voters=build_default_voters())
```

Registered as a `Strategy` DB row with
`class_path = "app.consensus.default_strategy:DefaultConsensusStrategy"`;
`manager.py`'s importlib loader picks it up.
`# ponytail:` paper bootstraps with default voter weights, not walk-forward
weights — load WF weights later if/when there's a real edge.

### 2. `RiskGuard` — `app/execution/guard.py`
Pure logic, injected clock. Consulted by the bot before every `place_order`,
so it sits outside the strategy.

```python
RiskGuard(max_daily_loss_pct: float, max_position_pct: float)
guard.check(is_reducing, intended_value, equity, daily_pnl, now) -> (allowed, reason)
guard.reset()
```

- Latches OFF on first `daily_pnl <= -equity * max_daily_loss_pct`.
- While latched: opening orders blocked, `is_reducing=True` orders allowed.
- Position cap: opening order with `intended_value > equity * max_position_pct`
  → rejected (reason returned), not shrunk.
- Auto-reset: when `now.date()` (UTC) advances past the latched date.

### 3. Persistence
- **`ConsensusSignal`** (new model + table): `id, asset_id (FK), timestamp,
  action, price, score, n_long, n_short, n_flat, votes (JSON), created_at`.
  One row per fired signal, sourced from `signal.metadata`.
- **Closed `Trade` rows**: add an optional `on_close` callback to
  `PaperTradingEngine` that fires at position close (it already has avg entry,
  exit fill, size, pnl, commission). The bot supplies a sink writing a closed
  `Trade` row (`is_paper=True`, `status=CLOSED`). Linked to `ConsensusSignal`
  by timestamp+asset; no FK (Phase 3 can join).

### 4. Bot loop wiring — `app/bots/bot.py` (minimal)
On fired signal: write `ConsensusSignal` → `guard.check(...)` →
place_order if allowed, else log rejection. Determine `is_reducing` from the
current position vs. signal action. Wire the engine `on_close` sink at
connector init. Live path untouched.

### 5. Entry point — `scripts/run_consensus_paper.py`
Builds a `BotConfig` (BTC/USDT, 5m, source=binance, paper,
`max_hold_minutes=0`, `close_before_market_close=False`), starts the bot via
asyncio. Mirrors `run_consensus_phase1.py`.

## Testing
- `test_risk_guard.py` — latch on breach; blocks opens / allows closes;
  auto-reset on UTC day rollover; position-cap rejection. Pure, injected clock.
- `test_consensus_paper.py` — `DefaultConsensusStrategy()` constructs & emits;
  `on_close` sink writes a `Trade`; `ConsensusSignal` row shape.
- Existing 60 tests stay green.

## Out of scope (YAGNI)
Frontend meter (Phase 3), paper-vs-backtest comparison (Phase 4), walk-forward
weight loading, multi-asset / market-hours, ML voters.
