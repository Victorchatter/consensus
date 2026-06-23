# Consensus Phase 2 — Paper Trading Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Run `ConsensusStrategy` continuously against real-time BTC/USDT bars through EchoTrader's paper engine + bot loop, persist per-trade vote breakdowns and closed trades to SQLite, and enforce a strategy-independent kill-switch / max-daily-loss / position cap.

**Architecture:** A zero-arg `DefaultConsensusStrategy` slots into the existing bot via the `class_path` importlib loader. A pure `RiskGuard` is consulted by the bot before every order (outside the strategy). A new `ConsensusSignal` table records every fired signal; closed `Trade` rows are written via a new `on_close` sink on the paper engine.

**Tech Stack:** Python 3.14, SQLAlchemy (SQLite), asyncio, CCXT (public OHLCV), pytest.

## Global Constraints

- Python 3.14, Windows. No compiled ML libs (no sklearn/catboost/xgboost/torch/numba). numpy/pandas OK.
- SQLite only (`database/echotrader.db`, gitignored). No Postgres/Redis.
- Run python via `./venv/Scripts/python.exe` from `echotrader/backend`.
- Use `127.0.0.1`, not `localhost`. Network I/O off the event loop.
- Live trading OFF by default. Do not enable `live_trading_enabled` or set `mode="live"`.
- Bars in via `load_bars()`; writes via `store_timestamp()`. Don't bypass.
- Test command: `cd backend && ./venv/Scripts/python.exe -m pytest tests/ -q` (60 tests currently pass; keep green).

---

### Task 1: `ConsensusSignal` audit model

**Files:**
- Modify: `backend/app/models/__init__.py` (add model after the `Trade` class)
- Test: `backend/tests/test_consensus_signal_model.py`

**Interfaces:**
- Produces: `models.ConsensusSignal` ORM class with columns `id, asset_id, timestamp, action, price, score, n_long, n_short, n_flat, votes (JSON), created_at`.

- [ ] **Step 1: Write the failing test**

```python
# backend/tests/test_consensus_signal_model.py
from app.core.database import Base, engine, SessionLocal
from app import models


def test_consensus_signal_roundtrip():
    Base.metadata.create_all(bind=engine)
    db = SessionLocal()
    try:
        row = models.ConsensusSignal(
            asset_id=1, timestamp=__import__("datetime").datetime(2026, 1, 1),
            action="buy", price=42000.0, score=0.72,
            n_long=9, n_short=2, n_flat=3, votes={"voterA": 1, "voterB": -1},
        )
        db.add(row); db.commit(); db.refresh(row)
        assert row.id is not None
        assert row.votes["voterA"] == 1
    finally:
        db.close()
```

- [ ] **Step 2: Run test, verify it fails**

Run: `./venv/Scripts/python.exe -m pytest tests/test_consensus_signal_model.py -v`
Expected: FAIL — `AttributeError: module 'app.models' has no attribute 'ConsensusSignal'`.

- [ ] **Step 3: Add the model** (after the `Trade` class in `app/models/__init__.py`)

```python
class ConsensusSignal(Base):
    __tablename__ = "consensus_signals"
    __table_args__ = (Index("ix_consensus_signal_asset_ts", "asset_id", "timestamp"),)

    id = Column(Integer, primary_key=True, index=True)
    asset_id = Column(Integer, ForeignKey("assets.id"), nullable=False)
    timestamp = Column(DateTime, nullable=False)
    action = Column(String(8), nullable=False)   # "buy" | "sell"
    price = Column(Float, nullable=False)
    score = Column(Float, nullable=False)
    n_long = Column(Integer, default=0)
    n_short = Column(Integer, default=0)
    n_flat = Column(Integer, default=0)
    votes = Column(JSON, nullable=False, default=dict)
    created_at = Column(DateTime, default=dt.datetime.utcnow)
```

(`Index`, `Column`, `ForeignKey`, `JSON`, `dt` are already imported at the top of this file.)

- [ ] **Step 4: Run test, verify it passes**

Run: `./venv/Scripts/python.exe -m pytest tests/test_consensus_signal_model.py -v`
Expected: PASS.

- [ ] **Step 5: Commit**

```bash
git add backend/app/models/__init__.py backend/tests/test_consensus_signal_model.py
git commit -m "feat(consensus): add ConsensusSignal audit model"
```

---

### Task 2: `RiskGuard` — strategy-independent execution guard

**Files:**
- Create: `backend/app/execution/guard.py`
- Test: `backend/tests/test_risk_guard.py`

**Interfaces:**
- Produces:
  - `RiskGuard(max_daily_loss_pct: float, max_position_pct: float)` — percentages as fractions (0.05 = 5%).
  - `guard.check(is_reducing: bool, intended_value: float, equity: float, daily_pnl: float, now: datetime) -> tuple[bool, str]`
  - `guard.reset() -> None`
  - `guard.latched -> bool` (attribute)

- [ ] **Step 1: Write the failing tests**

```python
# backend/tests/test_risk_guard.py
import datetime as dt
from app.execution.guard import RiskGuard

D1 = dt.datetime(2026, 1, 1, 10, 0)
D2 = dt.datetime(2026, 1, 2, 10, 0)


def test_allows_normal_opening_order():
    g = RiskGuard(max_daily_loss_pct=0.05, max_position_pct=0.20)
    ok, _ = g.check(is_reducing=False, intended_value=1000, equity=100_000, daily_pnl=0, now=D1)
    assert ok


def test_position_cap_rejects_oversized_open():
    g = RiskGuard(0.05, 0.20)
    ok, reason = g.check(False, intended_value=30_000, equity=100_000, daily_pnl=0, now=D1)
    assert not ok and "position" in reason.lower()


def test_latches_on_daily_loss_and_blocks_opens():
    g = RiskGuard(0.05, 0.20)
    ok, reason = g.check(False, 1000, equity=100_000, daily_pnl=-6000, now=D1)
    assert not ok and g.latched
    # stays latched even after pnl recovers, same day
    ok2, _ = g.check(False, 1000, equity=100_000, daily_pnl=0, now=D1)
    assert not ok2


def test_latched_still_allows_closing():
    g = RiskGuard(0.05, 0.20)
    g.check(False, 1000, 100_000, daily_pnl=-6000, now=D1)  # latch
    ok, _ = g.check(is_reducing=True, intended_value=1000, equity=100_000, daily_pnl=-6000, now=D1)
    assert ok


def test_auto_reset_on_utc_day_rollover():
    g = RiskGuard(0.05, 0.20)
    g.check(False, 1000, 100_000, daily_pnl=-6000, now=D1)  # latch on day 1
    ok, _ = g.check(False, 1000, 100_000, daily_pnl=0, now=D2)
    assert ok and not g.latched
```

- [ ] **Step 2: Run tests, verify they fail**

Run: `./venv/Scripts/python.exe -m pytest tests/test_risk_guard.py -v`
Expected: FAIL — `ModuleNotFoundError: No module named 'app.execution.guard'`.

- [ ] **Step 3: Implement `RiskGuard`**

```python
# backend/app/execution/guard.py
"""Execution-layer risk guard. Enforced outside the strategy: the bot consults
it before every order, so a strategy bug cannot bypass the kill-switch."""
from __future__ import annotations

import datetime as dt
from typing import Optional


class RiskGuard:
    def __init__(self, max_daily_loss_pct: float, max_position_pct: float):
        self.max_daily_loss_pct = max_daily_loss_pct
        self.max_position_pct = max_position_pct
        self.latched = False
        self._latched_date: Optional[dt.date] = None

    def reset(self) -> None:
        self.latched = False
        self._latched_date = None

    def check(self, is_reducing: bool, intended_value: float, equity: float,
              daily_pnl: float, now: dt.datetime) -> tuple[bool, str]:
        today = now.date()
        # Auto-reset latch at UTC day rollover.
        if self.latched and self._latched_date is not None and today > self._latched_date:
            self.reset()

        # Latch on daily-loss breach (engages even on a reducing order's check).
        if daily_pnl <= -abs(equity) * self.max_daily_loss_pct:
            if not self.latched:
                self.latched = True
                self._latched_date = today

        if is_reducing:
            return True, "ok (reducing)"

        if self.latched:
            return False, f"kill-switch latched (daily loss breach on {self._latched_date})"

        if intended_value > abs(equity) * self.max_position_pct:
            return False, (f"position cap: {intended_value:.2f} > "
                           f"{self.max_position_pct:.0%} of equity {equity:.2f}")
        return True, "ok"
```

- [ ] **Step 4: Run tests, verify they pass**

Run: `./venv/Scripts/python.exe -m pytest tests/test_risk_guard.py -v`
Expected: PASS (5 tests).

- [ ] **Step 5: Commit**

```bash
git add backend/app/execution/guard.py backend/tests/test_risk_guard.py
git commit -m "feat(execution): add strategy-independent RiskGuard kill-switch"
```

---

### Task 3: `on_close` sink on `PaperTradingEngine`

**Files:**
- Modify: `backend/app/execution/paper.py`
- Test: `backend/tests/test_paper_on_close.py`

**Interfaces:**
- Consumes: nothing.
- Produces: `PaperTradingEngine(initial_balance=..., on_close=callable|None)`. The
  `on_close` callable is invoked with one dict argument at every full position close:
  `{asset_id, symbol, direction ("long"|"short"), entry_price, exit_price, size, pnl, commission, exit_time (datetime)}`.

- [ ] **Step 1: Write the failing test**

```python
# backend/tests/test_paper_on_close.py
from app.execution.paper import PaperTradingEngine


def test_on_close_fires_for_long_roundtrip():
    closed = []
    eng = PaperTradingEngine(initial_balance=100_000.0, on_close=closed.append)
    eng.place_order(asset_id=1, symbol="BTC/USDT", action="buy", size=1.0)
    eng.on_price_update(1, "BTC/USDT", 40_000.0)   # fill the open
    eng.place_order(asset_id=1, symbol="BTC/USDT", action="sell", size=1.0)
    eng.on_price_update(1, "BTC/USDT", 41_000.0)   # fill the close
    assert len(closed) == 1
    t = closed[0]
    assert t["direction"] == "long"
    assert t["size"] == 1.0
    assert t["exit_price"] > t["entry_price"]
    assert t["pnl"] is not None
```

- [ ] **Step 2: Run test, verify it fails**

Run: `./venv/Scripts/python.exe -m pytest tests/test_paper_on_close.py -v`
Expected: FAIL — `TypeError: __init__() got an unexpected keyword argument 'on_close'`.

- [ ] **Step 3: Implement**

In `PaperTradingEngine.__init__`, add the parameter and store it:

```python
    def __init__(self, initial_balance: float = 100_000.0, on_close=None):
        self.account = PaperAccount(balance=initial_balance)
        self._commission_pct = 0.001
        self._slippage_pct = 0.0005
        self._max_daily_loss_pct = settings.max_daily_loss_pct
        self._max_position_size_pct = settings.max_position_size_pct
        self._on_close = on_close
```

Add a private helper (anywhere in the class):

```python
    def _emit_close(self, pos, fill_price, size, pnl, commission):
        if self._on_close is None:
            return
        self._on_close({
            "asset_id": pos.asset_id,
            "symbol": pos.symbol,
            "direction": pos.direction,
            "entry_price": pos.avg_entry_price,
            "exit_price": fill_price,
            "size": size,
            "pnl": pnl,
            "commission": commission,
            "exit_time": dt.datetime.utcnow(),
        })
```

Call `self._emit_close(...)` at BOTH full-close points in `_fill_order`, immediately before the `del self.account.positions[...]` lines:

1. Short full-close branch (`if order.size >= pos.size:`):
```python
                    self._emit_close(pos, fill_price, pos.size, pnl, commission)
                    del self.account.positions[order.asset_id]
```
2. Long close branch (`if pos.size <= 0:`):
```python
                    self._emit_close(pos, fill_price, sell_size, pnl, commission)
                    del self.account.positions[order.asset_id]
```

(Place each `_emit_close` call after `pnl` is computed and counters updated, before the `del`. `pos` still holds `avg_entry_price` and `direction` at that point.)

- [ ] **Step 4: Run test, verify it passes; run full suite**

Run: `./venv/Scripts/python.exe -m pytest tests/test_paper_on_close.py -v && ./venv/Scripts/python.exe -m pytest tests/ -q`
Expected: new test PASS; all prior tests still PASS.

- [ ] **Step 5: Commit**

```bash
git add backend/app/execution/paper.py backend/tests/test_paper_on_close.py
git commit -m "feat(execution): emit on_close sink from paper engine at position close"
```

---

### Task 4: `DefaultConsensusStrategy` + DB registration helper

**Files:**
- Create: `backend/app/consensus/default_strategy.py`
- Test: `backend/tests/test_default_strategy.py`

**Interfaces:**
- Consumes: `ConsensusStrategy` (base.py), `build_default_voters` (voters.py).
- Produces:
  - `DefaultConsensusStrategy()` — zero-arg, constructs with `build_default_voters()`.
  - `CONSENSUS_CLASS_PATH = "app.consensus.default_strategy:DefaultConsensusStrategy"`.
  - `register_strategy(db) -> models.Strategy` — idempotent upsert of the Strategy row (by unique `name`).

- [ ] **Step 1: Write the failing tests**

```python
# backend/tests/test_default_strategy.py
from app.consensus.default_strategy import DefaultConsensusStrategy, CONSENSUS_CLASS_PATH


def test_constructs_with_no_args_and_has_voters():
    s = DefaultConsensusStrategy()
    assert len(s.voters) > 0


def test_class_path_resolves_via_importlib():
    import importlib
    module_path, class_name = CONSENSUS_CLASS_PATH.rsplit(":", 1)
    cls = getattr(importlib.import_module(module_path), class_name)
    assert cls is DefaultConsensusStrategy
    assert cls() is not None  # zero-arg construct, matches bot.py self.strategy_class()
```

- [ ] **Step 2: Run tests, verify they fail**

Run: `./venv/Scripts/python.exe -m pytest tests/test_default_strategy.py -v`
Expected: FAIL — `ModuleNotFoundError: No module named 'app.consensus.default_strategy'`.

- [ ] **Step 3: Implement**

```python
# backend/app/consensus/default_strategy.py
"""Zero-arg consensus strategy so the bot's `self.strategy_class()` contract
works unchanged. Registered in the Strategy table via `register_strategy`."""
from __future__ import annotations

from app.consensus.base import ConsensusStrategy
from app.consensus.voters import build_default_voters
from app import models

CONSENSUS_CLASS_PATH = "app.consensus.default_strategy:DefaultConsensusStrategy"


class DefaultConsensusStrategy(ConsensusStrategy):
    name = "Ensemble Consensus (default)"

    def __init__(self):
        # ponytail: paper bootstraps with default voter weights, not walk-forward
        # weights — load WF weights here later if a real edge shows up.
        super().__init__(voters=build_default_voters())


def register_strategy(db) -> "models.Strategy":
    """Idempotent: ensure a Strategy row points at DefaultConsensusStrategy."""
    row = db.query(models.Strategy).filter_by(name=DefaultConsensusStrategy.name).one_or_none()
    if row is None:
        row = models.Strategy(
            name=DefaultConsensusStrategy.name,
            class_path=CONSENSUS_CLASS_PATH,
            params_schema={},
            description="Weighted supermajority vote across independent voters.",
            is_builtin=True,
        )
        db.add(row); db.commit(); db.refresh(row)
    elif row.class_path != CONSENSUS_CLASS_PATH:
        row.class_path = CONSENSUS_CLASS_PATH
        db.commit()
    return row
```

- [ ] **Step 4: Run tests, verify they pass**

Run: `./venv/Scripts/python.exe -m pytest tests/test_default_strategy.py -v`
Expected: PASS.

- [ ] **Step 5: Commit**

```bash
git add backend/app/consensus/default_strategy.py backend/tests/test_default_strategy.py
git commit -m "feat(consensus): zero-arg DefaultConsensusStrategy + DB registration"
```

---

### Task 5: Wire guard + audit logging + close sink into the bot loop

**Files:**
- Modify: `backend/app/bots/bot.py`
- Test: `backend/tests/test_bot_consensus_wiring.py`

**Interfaces:**
- Consumes: `RiskGuard` (Task 2), `models.ConsensusSignal` (Task 1), engine `on_close` (Task 3).
- Produces: bot methods `_log_consensus_signal(session, asset_id, signal)`, `_write_closed_trade(trade: dict)`, and a `self._guard: RiskGuard`. Order placement is gated by `self._guard.check(...)`.

The bot already imports `from app import models` and `from sqlalchemy.orm import Session`. Add `from app.execution.guard import RiskGuard` at the top.

- [ ] **Step 1: Write the failing tests** (unit-level, no network)

```python
# backend/tests/test_bot_consensus_wiring.py
import datetime as dt
from app.bots.bot import TradingBot, BotConfig
from app.core.database import Base, engine, SessionLocal
from app import models
from app.strategies import Signal


def _bot():
    cfg = BotConfig(id="t1", name="t", strategy_id=1, asset_ids=[1],
                    timeframe="5m", data_source="binance", broker="paper",
                    risk_max_daily_loss_pct=5.0, risk_max_position_size_pct=20.0)
    return TradingBot(cfg, DefaultConsensusStrategyStub, SessionLocal)


class DefaultConsensusStrategyStub:
    def __init__(self): pass


def test_guard_is_constructed_from_config():
    b = _bot()
    assert b._guard.max_daily_loss_pct == 0.05
    assert b._guard.max_position_pct == 0.20


def test_log_consensus_signal_writes_row():
    Base.metadata.create_all(bind=engine)
    b = _bot()
    sig = Signal(timestamp=dt.datetime(2026, 1, 1), action="buy", price=40000.0,
                 metadata={"score": 0.7, "n_long": 9, "n_short": 2, "n_flat": 3,
                           "votes": {"a": 1}})
    db = SessionLocal()
    try:
        b._log_consensus_signal(db, asset_id=1, signal=sig)
        rows = db.query(models.ConsensusSignal).filter_by(asset_id=1).all()
        assert len(rows) >= 1 and rows[-1].score == 0.7
    finally:
        db.close()
```

- [ ] **Step 2: Run tests, verify they fail**

Run: `./venv/Scripts/python.exe -m pytest tests/test_bot_consensus_wiring.py -v`
Expected: FAIL — `AttributeError: 'TradingBot' object has no attribute '_guard'`.

- [ ] **Step 3: Implement the wiring**

3a. In `TradingBot.__init__`, after `self._live_confirmed = False`, add:

```python
        self._guard = RiskGuard(
            max_daily_loss_pct=self.config.risk_max_daily_loss_pct / 100.0,
            max_position_pct=self.config.risk_max_position_size_pct / 100.0,
        )
```

3b. Add the two helper methods to `TradingBot`:

```python
    def _log_consensus_signal(self, session: Session, asset_id: int, signal):
        md = signal.metadata or {}
        session.add(models.ConsensusSignal(
            asset_id=asset_id,
            timestamp=signal.timestamp,
            action=signal.action,
            price=float(signal.price),
            score=float(md.get("score", 0.0)),
            n_long=int(md.get("n_long", 0)),
            n_short=int(md.get("n_short", 0)),
            n_flat=int(md.get("n_flat", 0)),
            votes=md.get("votes", {}),
        ))
        session.commit()

    def _write_closed_trade(self, trade: dict):
        from app.models import TradeDirection, TradeStatus, OrderType
        with self._db() as session:
            direction = TradeDirection.LONG if trade["direction"] == "long" else TradeDirection.SHORT
            session.add(models.Trade(
                strategy_id=self.config.strategy_id,
                asset_id=trade["asset_id"],
                direction=direction,
                order_type=OrderType.MARKET,
                entry_time=trade["exit_time"],   # exit_time is when we learn the round-trip; entry approx
                exit_time=trade["exit_time"],
                entry_price=trade["entry_price"],
                exit_price=trade["exit_price"],
                size=trade["size"],
                pnl=trade["pnl"],
                commission=trade["commission"],
                status=TradeStatus.CLOSED,
                is_paper=True,
            ))
            session.commit()
```

3c. Wire the `on_close` sink onto the paper engine in `_init_connector`. At the end of that method, before the final `return get_connector(...)` for the paper default, capture the connector and attach the sink:

```python
        # Default to paper
        connector = get_connector("paper", paper=True, credentials={"initial_balance": self.config.initial_cash})
        if hasattr(connector, "_engine"):
            connector._engine._on_close = self._write_closed_trade
        return connector
```

3d. In `_run_loop`, where a signal fires (currently the `if signal:` block), replace the body so it logs the audit row and consults the guard before placing the order. Replace the existing `if signal:` block with:

```python
                        if signal:
                            self._log_consensus_signal(session, asset_id, signal)
                            size = self._compute_position_size(asset_id, signal.price)
                            if size > 0:
                                if self.config.mode == "live" and not self._live_confirmed:
                                    self._log(f"[BLOCKED] {asset.symbol} {signal.action.upper()} — live mode not confirmed")
                                    continue

                                # Strategy-independent execution guard.
                                is_reducing = strat._position is None  # signal that closes a position
                                acct = self._connector.get_account()
                                equity = acct.equity if acct.equity > 0 else acct.balance
                                ok, reason = self._guard.check(
                                    is_reducing=is_reducing,
                                    intended_value=size * signal.price,
                                    equity=equity,
                                    daily_pnl=self._connector.get_summary().get("realized_pnl", 0.0)
                                        if hasattr(self._connector, "get_summary") else 0.0,
                                    now=dt.datetime.utcnow(),
                                )
                                if not ok:
                                    self._log(f"[GUARD] {asset.symbol} {signal.action.upper()} rejected — {reason}")
                                    continue

                                order = self._connector.place_order(
                                    asset_id=asset_id,
                                    symbol=asset.symbol,
                                    action=signal.action,
                                    size=size,
                                    order_type="market",
                                    price=signal.price,
                                )
                                self._log(
                                    f"[{asset.symbol}] {signal.action.upper()} {size:.4f} @ {signal.price:.2f} — order={order.order_id} status={order.status}"
                                )
```

Note on `is_reducing`: `ConsensusStrategy.on_bar` sets `self._position = None` when it emits a closing order, so checking `strat._position is None` right after `on_bar` distinguishes a close (reducing) from an open. `# ponytail: works because consensus is single-position-per-asset; revisit if pyramiding is added.`

- [ ] **Step 4: Run tests, verify they pass; run full suite**

Run: `./venv/Scripts/python.exe -m pytest tests/test_bot_consensus_wiring.py -v && ./venv/Scripts/python.exe -m pytest tests/ -q`
Expected: new tests PASS; all prior tests PASS.

- [ ] **Step 5: Commit**

```bash
git add backend/app/bots/bot.py backend/tests/test_bot_consensus_wiring.py
git commit -m "feat(bots): wire RiskGuard, consensus audit logging, and close sink into bot loop"
```

---

### Task 6: Runnable paper entry point

**Files:**
- Create: `backend/scripts/run_consensus_paper.py`
- Test: `backend/tests/test_run_consensus_paper.py` (import/build only — no event loop run)

**Interfaces:**
- Consumes: `register_strategy` (Task 4), `BotManager`/`BotConfig`, `models`.
- Produces: `build_paper_bot_config(strategy_id: int) -> BotConfig` and a `main()` async entry point.

- [ ] **Step 1: Write the failing test**

```python
# backend/tests/test_run_consensus_paper.py
from scripts.run_consensus_paper import build_paper_bot_config


def test_paper_config_is_btc_paper_247():
    cfg = build_paper_bot_config(strategy_id=1)
    assert cfg.mode == "paper"
    assert cfg.data_source == "binance"
    assert cfg.timeframe == "5m"
    assert cfg.max_hold_minutes == 0
    assert cfg.close_before_market_close is False
```

- [ ] **Step 2: Run test, verify it fails**

Run: `./venv/Scripts/python.exe -m pytest tests/test_run_consensus_paper.py -v`
Expected: FAIL — `ModuleNotFoundError: No module named 'scripts.run_consensus_paper'`.

(If `scripts` is not importable, add an empty `backend/scripts/__init__.py` as part of this task.)

- [ ] **Step 3: Implement**

```python
# backend/scripts/run_consensus_paper.py
"""Start a paper-trading bot running DefaultConsensusStrategy on BTC/USDT 5m.
Live stays OFF. Run: ./venv/Scripts/python.exe -m scripts.run_consensus_paper"""
from __future__ import annotations

import asyncio

from app.core.database import Base, engine, SessionLocal
from app import models
from app.bots.bot import BotConfig
from app.bots.manager import manager
from app.consensus.default_strategy import register_strategy


def _ensure_btc_asset(db) -> int:
    asset = db.query(models.Asset).filter_by(symbol="BTC/USDT").one_or_none()
    if asset is None:
        asset = models.Asset(symbol="BTC/USDT", name="Bitcoin", asset_class=models.AssetClass.CRYPTO)
        db.add(asset); db.commit(); db.refresh(asset)
    return asset.id


def build_paper_bot_config(strategy_id: int, asset_id: int = 1) -> BotConfig:
    return BotConfig(
        id="consensus-paper-btc",
        name="Consensus Paper BTC/USDT",
        strategy_id=strategy_id,
        asset_ids=[asset_id],
        timeframe="5m",
        data_source="binance",
        broker="paper",
        mode="paper",                    # live OFF
        risk_max_daily_loss_pct=5.0,
        risk_max_position_size_pct=20.0,
        max_hold_minutes=0,              # 24/7 crypto, no scalp auto-close
        close_before_market_close=False,
    )


async def main():
    Base.metadata.create_all(bind=engine)
    db = SessionLocal()
    try:
        strat = register_strategy(db)
        asset_id = _ensure_btc_asset(db)
        cfg = build_paper_bot_config(strategy_id=strat.id, asset_id=asset_id)
    finally:
        db.close()
    bot = manager.create_bot(cfg)
    if bot is None:
        raise SystemExit("failed to create bot — check Strategy registration")
    print(f"Starting paper bot {cfg.name} (live OFF). Ctrl-C to stop.")
    await manager.start_bot(cfg.id)
    try:
        while True:
            await asyncio.sleep(60)
            print(bot.get_state()["paper_summary"])
    except KeyboardInterrupt:
        await manager.stop_bot(cfg.id)


if __name__ == "__main__":
    asyncio.run(main())
```

(Confirm `models.AssetClass.CRYPTO` exists; if the enum member differs, use the correct crypto member.)

- [ ] **Step 4: Run test, verify it passes; run full suite**

Run: `./venv/Scripts/python.exe -m pytest tests/test_run_consensus_paper.py -v && ./venv/Scripts/python.exe -m pytest tests/ -q`
Expected: PASS; all prior tests PASS (target: 60 + new tests).

- [ ] **Step 5: Commit**

```bash
git add backend/scripts/run_consensus_paper.py backend/tests/test_run_consensus_paper.py backend/scripts/__init__.py
git commit -m "feat(consensus): runnable BTC/USDT paper-trading entry point"
```

---

## Final verification

- [ ] Run full suite: `cd backend && ./venv/Scripts/python.exe -m pytest tests/ -q` — all green.
- [ ] Confirm no new dependencies added (no compiled ML libs).
- [ ] Confirm `live_trading_enabled` still False and `mode="paper"` everywhere.
- [ ] Update `HANDOFF.md` §2/§8 to mark Phase 2 done and point Phase 3 at the new tables.

## Self-review notes
- Spec §Component 1–5 each map to Tasks 4, 2, 1+3, 5, 6 respectively. ✓
- Kill-switch latch + auto-reset + allow-close + position-cap-reject: Task 2 tests. ✓
- Audit table + closed Trades: Tasks 1, 3, 5. ✓
- BTC/USDT 24/7 paper, live OFF: Task 6. ✓
