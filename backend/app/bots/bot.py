from __future__ import annotations

import asyncio
import datetime as dt
import traceback
from typing import Dict, Optional, Any, List
from dataclasses import dataclass, field

from app.exchange.base import ExchangeConnector
from app.exchange import get_connector
from app.strategies import Strategy, Bar
from app.data.feeders import get_feeder_for_source, OHLCVBar
from app import models
from app.execution.guard import RiskGuard
from sqlalchemy.orm import Session


@dataclass
class BotConfig:
    id: str
    name: str
    strategy_id: int
    asset_ids: List[int]
    timeframe: str = "1d"
    data_source: str = "yahoo"
    broker: str = "paper"  # paper, alpaca, ccxt
    broker_connection_id: Optional[int] = None
    initial_cash: float = 100_000.0
    mode: str = "paper"    # paper, live
    risk_max_daily_loss_pct: float = 2.0
    risk_max_position_size_pct: float = 10.0
    active: bool = False
    error_log: List[str] = field(default_factory=list)
    last_run_at: Optional[dt.datetime] = None
    # Scalp / intraday settings
    max_hold_minutes: int = 120       # Auto-close positions after N minutes (0 = disabled)
    close_before_market_close: bool = True  # Flatten all positions before 16:00 EST


class TradingBot:
    """Event-driven trading bot that evaluates strategies on incoming bars."""

    def __init__(self, config: BotConfig, strategy_class: type, db_session_factory):
        self.config = config
        self.strategy_class = strategy_class
        self._db = db_session_factory
        self._connector: Optional[ExchangeConnector] = None
        self._strategies: Dict[int, Strategy] = {}
        self._running = False
        self._task: Optional[asyncio.Task] = None
        self._last_bar: Dict[int, OHLCVBar] = {}
        self._live_confirmed: bool = False  # Safety guard: user must confirm first live run
        self._guard = RiskGuard(
            max_daily_loss_pct=self.config.risk_max_daily_loss_pct / 100.0,
            max_position_pct=self.config.risk_max_position_size_pct / 100.0,
        )
        # Daily-loss baseline: equity snapshot at the start of the current UTC
        # day, so the guard sees today's drawdown, not cumulative PnL.
        self._daily_baseline_equity: Optional[float] = None
        self._daily_baseline_date: Optional[dt.date] = None

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

    def _daily_pnl(self, equity: float, now: dt.datetime) -> float:
        """Equity change since the first observation of the current UTC day.
        Re-baselines on day rollover so the guard enforces a DAILY loss limit."""
        today = now.date()
        if self._daily_baseline_date != today:
            self._daily_baseline_date = today
            self._daily_baseline_equity = equity
        base = self._daily_baseline_equity if self._daily_baseline_equity is not None else equity
        return equity - base

    def _ensure_daily_baseline(self, now: dt.datetime) -> None:
        """Snapshot equity at the first loop tick of each UTC day so the daily-loss
        guard measures from day-start even if no signal has fired yet."""
        today = now.date()
        if self._daily_baseline_date == today:
            return
        if self._connector is None:
            return
        try:
            acct = self._connector.get_account()
            equity = acct.equity if acct.equity > 0 else acct.balance
        except Exception:
            return
        self._daily_baseline_date = today
        self._daily_baseline_equity = equity

    def _init_connector(self) -> ExchangeConnector:
        """Create the appropriate exchange connector for this bot's mode."""
        if self.config.mode == "live":
            # Look up broker credentials
            with self._db() as session:
                conn = session.query(models.BrokerConnection).get(self.config.broker_connection_id or 0)
                if not conn:
                    self._log("WARN: Live mode requested but no broker connection found. Falling back to paper.")
                    return get_connector("paper", paper=True, credentials={"initial_balance": self.config.initial_cash})

                api_key = conn.api_key_encrypted or ""
                api_secret = conn.api_secret_encrypted or ""

                # Attempt naive decrypt if it looks like Fernet ciphertext
                if api_key.startswith("gAAAA"):
                    self._log("WARN: Encrypted API key but no master password provided. Falling back to paper.")
                    return get_connector("paper", paper=True, credentials={"initial_balance": self.config.initial_cash})

                return get_connector(
                    conn.broker_name,
                    paper=conn.is_paper,
                    credentials={
                        "api_key": api_key,
                        "api_secret": api_secret,
                        "passphrase": conn.passphrase_encrypted or "",
                        "initial_balance": self.config.initial_cash,
                    },
                )

        # Default to paper
        connector = get_connector("paper", paper=True, credentials={"initial_balance": self.config.initial_cash})
        if hasattr(connector, "_engine"):
            connector._engine._on_close = self._write_closed_trade
        return connector

    async def start(self):
        if self._running:
            return

        # Safety guard for live mode
        if self.config.mode == "live" and not self._live_confirmed:
            self._log("LIVE MODE: Bot requires explicit confirmation before placing real orders.")
            # Bot will start but won't trade until _live_confirmed is True.
            # The API layer should set this after user confirmation.

        self._connector = self._init_connector()
        self._running = True
        self.config.active = True
        self.config.error_log = []
        self._task = asyncio.create_task(self._run_loop())

    def confirm_live(self):
        """Call this after the user explicitly confirms they want to run live trades."""
        self._live_confirmed = True
        self._log("LIVE MODE CONFIRMED by user.")

    async def stop(self):
        self._running = False
        self.config.active = False
        if self._task:
            self._task.cancel()
            try:
                await self._task
            except asyncio.CancelledError:
                pass
            self._task = None

    async def _run_loop(self):
        """Main event loop: fetch bars, evaluate strategy, execute signals."""
        feeder = get_feeder_for_source(self.config.data_source)
        while self._running:
            try:
                self._ensure_daily_baseline(dt.datetime.utcnow())
                with self._db() as session:
                    for asset_id in self.config.asset_ids:
                        asset = session.query(models.Asset).get(asset_id)
                        if not asset:
                            continue

                        # Fetch latest bar
                        end = dt.date.today()
                        start = end - dt.timedelta(days=7)
                        bars = feeder.fetch_historical(
                            asset.symbol, start, end, self.config.timeframe
                        )
                        if not bars:
                            continue

                        latest = bars[-1]
                        prev = self._last_bar.get(asset_id)
                        if prev and latest.timestamp == prev.timestamp:
                            # No new bar yet
                            continue

                        self._last_bar[asset_id] = latest

                        # Create or reuse strategy instance per asset
                        strat = self._strategies.get(asset_id)
                        if strat is None:
                            strat = self.strategy_class()
                            self._strategies[asset_id] = strat

                        bar = Bar(
                            timestamp=latest.timestamp,
                            open=latest.open,
                            high=latest.high,
                            low=latest.low,
                            close=latest.close,
                            volume=latest.volume or 0.0,
                        )
                        signal = strat.on_bar(bar)

                        if signal:
                            self._log_consensus_signal(session, asset_id, signal)
                            size = self._compute_position_size(asset_id, signal.price)
                            if size > 0:
                                if self.config.mode == "live" and not self._live_confirmed:
                                    self._log(f"[BLOCKED] {asset.symbol} {signal.action.upper()} — live mode not confirmed")
                                    continue

                                # Strategy-independent execution guard.
                                is_reducing = getattr(strat, "_position", None) is None  # closing signal
                                acct = self._connector.get_account()
                                equity = acct.equity if acct.equity > 0 else acct.balance
                                ok, reason = self._guard.check(
                                    is_reducing=is_reducing,
                                    intended_value=size * signal.price,
                                    equity=equity,
                                    daily_pnl=self._daily_pnl(equity, dt.datetime.utcnow()),
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

                # ── Intraday / scalp guards ──
                self._enforce_scalp_guards()

                self.config.last_run_at = dt.datetime.utcnow()
                await asyncio.sleep(60)  # Poll every minute
            except Exception as e:
                err = f"Bot loop error: {e}\n{traceback.format_exc()[-200:]}"
                self._log(err)
                await asyncio.sleep(60)

    def _enforce_scalp_guards(self):
        """Close positions that exceed max hold time or are open near market close."""
        now = dt.datetime.utcnow()
        positions = self._connector.get_positions()

        # 1) Max hold time guard
        if self.config.max_hold_minutes > 0:
            for pos in positions:
                # For paper we can check orders; for live we approximate with current time
                # since live connectors don't expose order history here.
                # Use a simple heuristic: if we haven't seen this position before, record it.
                entry_key = f"entry_{pos.asset_id}"
                if not hasattr(self, "_entry_times"):
                    self._entry_times = {}
                if entry_key not in self._entry_times:
                    self._entry_times[entry_key] = now
                entry_time = self._entry_times[entry_key]
                elapsed = (now - entry_time).total_seconds() / 60
                if elapsed > self.config.max_hold_minutes:
                    action = "sell" if pos.direction == "long" else "buy"
                    self._connector.place_order(
                        asset_id=pos.asset_id,
                        symbol=pos.symbol,
                        action=action,
                        size=pos.size,
                        order_type="market",
                    )
                    self._entry_times.pop(entry_key, None)
                    self._log(
                        f"[SCALP GUARD] Force-close {pos.symbol} {pos.direction} {pos.size:.4f} after {self.config.max_hold_minutes}min"
                    )

        # 2) Market-close guard (US equities 16:00 ET)
        if self.config.close_before_market_close:
            try:
                from zoneinfo import ZoneInfo
                ny_now = now.replace(tzinfo=dt.timezone.utc).astimezone(ZoneInfo("America/New_York"))
                # Flatten everything after 15:55 ET (5 min buffer before 16:00)
                if ny_now.hour == 15 and ny_now.minute >= 55:
                    for pos in positions:
                        action = "sell" if pos.direction == "long" else "buy"
                        self._connector.place_order(
                            asset_id=pos.asset_id,
                            symbol=pos.symbol,
                            action=action,
                            size=pos.size,
                            order_type="market",
                        )
                        self._log(
                            f"[MARKET CLOSE] Flatten {pos.symbol} {pos.direction} {pos.size:.4f} before 16:00 ET"
                        )
            except Exception:
                pass

    def _compute_position_size(self, asset_id: int, price: float) -> float:
        """Default position sizing: 20% of equity per signal."""
        try:
            account = self._connector.get_account()
            equity = account.equity if account.equity > 0 else account.balance
        except Exception:
            equity = self.config.initial_cash
        target_value = equity * 0.20
        size = target_value / price if price > 0 else 0.0
        return round(size, 6)

    def _log(self, message: str):
        ts = dt.datetime.utcnow().isoformat()
        self.config.error_log.append(f"[{ts}] {message}")
        if len(self.config.error_log) > 500:
            self.config.error_log = self.config.error_log[-500:]

    def get_state(self) -> Dict[str, Any]:
        connector_summary = {}
        positions = []
        recent_orders = []
        try:
            if self._connector:
                account = self._connector.get_account()
                connector_summary = {
                    "balance": account.balance,
                    "equity": account.equity,
                    "buying_power": account.buying_power,
                }
                positions = [
                    {
                        "asset_id": p.asset_id,
                        "symbol": p.symbol,
                        "direction": p.direction,
                        "size": p.size,
                        "avg_entry_price": p.avg_entry_price,
                        "unrealized_pnl": p.unrealized_pnl,
                    }
                    for p in self._connector.get_positions()
                ]
                # Paper connector exposes orders; live connectors don't track history
                # So we only show orders if the connector has them
                if hasattr(self._connector, "get_summary"):
                    connector_summary = self._connector.get_summary()
                if hasattr(self._connector, "_engine"):
                    recent_orders = [
                        {
                            "id": o.id,
                            "symbol": o.symbol,
                            "action": o.action,
                            "size": o.size,
                            "status": o.status,
                            "fill_price": o.fill_price,
                            "pnl": o.pnl,
                            "created_at": o.created_at.isoformat(),
                        }
                        for o in reversed(self._connector._engine.account.orders[-20:])
                    ]
        except Exception as e:
            connector_summary = {"error": str(e)}

        return {
            "config": {
                "id": self.config.id,
                "name": self.config.name,
                "active": self.config.active,
                "strategy_id": self.config.strategy_id,
                "asset_ids": self.config.asset_ids,
                "timeframe": self.config.timeframe,
                "data_source": self.config.data_source,
                "broker": self.config.broker,
                "mode": self.config.mode,
                "broker_connection_id": self.config.broker_connection_id,
                "last_run_at": self.config.last_run_at.isoformat() if self.config.last_run_at else None,
            },
            "paper_summary": connector_summary,
            "positions": positions,
            "recent_orders": recent_orders,
            "error_log": self.config.error_log[-50:],
        }
