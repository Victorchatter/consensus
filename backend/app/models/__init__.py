from __future__ import annotations

import datetime as dt
from enum import Enum as PyEnum
from typing import Optional

from sqlalchemy import (
    Column, Integer, String, Float, DateTime, Boolean, Text, ForeignKey,
    JSON, Enum, Date, UniqueConstraint, Index
)
from sqlalchemy.orm import relationship

from app.core.database import Base


class AssetClass(str, PyEnum):
    STOCK = "stock"
    ETF = "etf"
    CRYPTO = "crypto"
    FOREX = "forex"
    COMMODITY = "commodity"
    INDEX = "index"


class TradeDirection(str, PyEnum):
    LONG = "long"
    SHORT = "short"


class TradeStatus(str, PyEnum):
    OPEN = "open"
    CLOSED = "closed"
    CANCELLED = "cancelled"


class OrderType(str, PyEnum):
    MARKET = "market"
    LIMIT = "limit"
    STOP = "stop"
    STOP_LIMIT = "stop_limit"
    OCO = "oco"


class BacktestStatus(str, PyEnum):
    PENDING = "pending"
    RUNNING = "running"
    COMPLETED = "completed"
    FAILED = "failed"


class MarketRegimeLabel(str, PyEnum):
    TRENDING = "trending"
    RANGING = "ranging"
    VOLATILE = "volatile"
    QUIET = "quiet"


# ── ASSETS ──────────────────────────────────────────────────────

class Asset(Base):
    __tablename__ = "assets"

    id = Column(Integer, primary_key=True, index=True)
    symbol = Column(String(32), nullable=False, index=True)
    name = Column(String(256), nullable=True)
    asset_class = Column(Enum(AssetClass), nullable=False, default=AssetClass.STOCK)
    exchange = Column(String(64), nullable=True)
    data_source = Column(String(32), nullable=True, default="yahoo")
    is_active = Column(Boolean, default=True, nullable=False)
    created_at = Column(DateTime, default=dt.datetime.utcnow)

    price_bars = relationship("PriceBar", back_populates="asset", cascade="all, delete-orphan")
    quotes = relationship("Quote", back_populates="asset", cascade="all, delete-orphan")
    trades = relationship("Trade", back_populates="asset")

    __table_args__ = (UniqueConstraint("symbol", "exchange", name="uix_symbol_exchange"),)


# ── PRICE BARS ──────────────────────────────────────────────────

class PriceBar(Base):
    __tablename__ = "price_bars"
    __table_args__ = (
        UniqueConstraint("asset_id", "timestamp", "timeframe", name="uix_bar"),
        Index("ix_bar_lookup", "asset_id", "timeframe", "timestamp"),
    )

    id = Column(Integer, primary_key=True)
    asset_id = Column(Integer, ForeignKey("assets.id"), nullable=False)
    timestamp = Column(DateTime, nullable=False)
    timeframe = Column(String(8), nullable=False, default="1d")  # 1m,5m,15m,1h,4h,1d,1w,1m
    open = Column(Float, nullable=False)
    high = Column(Float, nullable=False)
    low = Column(Float, nullable=False)
    close = Column(Float, nullable=False)
    volume = Column(Float, nullable=True)
    created_at = Column(DateTime, default=dt.datetime.utcnow)

    asset = relationship("Asset", back_populates="price_bars")


# ── QUOTES (REAL-TIME) ──────────────────────────────────────────

class Quote(Base):
    __tablename__ = "quotes"
    __table_args__ = (Index("ix_quote_latest", "asset_id", "timestamp"),)

    id = Column(Integer, primary_key=True)
    asset_id = Column(Integer, ForeignKey("assets.id"), nullable=False)
    timestamp = Column(DateTime, nullable=False, default=dt.datetime.utcnow)
    bid = Column(Float, nullable=True)
    ask = Column(Float, nullable=True)
    last_price = Column(Float, nullable=False)
    volume = Column(Float, nullable=True)

    asset = relationship("Asset", back_populates="quotes")


# ── STRATEGIES ──────────────────────────────────────────────────

class Strategy(Base):
    __tablename__ = "strategies"

    id = Column(Integer, primary_key=True, index=True)
    name = Column(String(128), nullable=False, unique=True)
    class_path = Column(String(256), nullable=False)
    params_schema = Column(JSON, nullable=False, default=dict)
    description = Column(Text, nullable=True)
    is_active = Column(Boolean, default=True, nullable=False)
    is_builtin = Column(Boolean, default=True, nullable=False)
    created_at = Column(DateTime, default=dt.datetime.utcnow)

    backtest_runs = relationship("BacktestRun", back_populates="strategy")
    trades = relationship("Trade", back_populates="strategy")


# ── BACKTEST RUNS ─────────────────────────────────────────────

class BacktestRun(Base):
    __tablename__ = "backtest_runs"

    id = Column(Integer, primary_key=True, index=True)
    strategy_id = Column(Integer, ForeignKey("strategies.id"), nullable=False)
    start_date = Column(Date, nullable=False)
    end_date = Column(Date, nullable=False)
    params = Column(JSON, nullable=False, default=dict)
    metrics_json = Column(JSON, nullable=True)
    equity_curve_json = Column(JSON, nullable=True)
    trades_json = Column(JSON, nullable=True)
    status = Column(Enum(BacktestStatus), default=BacktestStatus.PENDING, nullable=False)
    error_message = Column(Text, nullable=True)
    created_at = Column(DateTime, default=dt.datetime.utcnow)
    completed_at = Column(DateTime, nullable=True)

    strategy = relationship("Strategy", back_populates="backtest_runs")


# ── TRADES ──────────────────────────────────────────────────────

class Trade(Base):
    __tablename__ = "trades"
    __table_args__ = (Index("ix_trade_status", "status"), Index("ix_trade_dates", "entry_time", "exit_time"))

    id = Column(Integer, primary_key=True, index=True)
    strategy_id = Column(Integer, ForeignKey("strategies.id"), nullable=True)
    asset_id = Column(Integer, ForeignKey("assets.id"), nullable=False)
    direction = Column(Enum(TradeDirection), nullable=False)
    order_type = Column(Enum(OrderType), default=OrderType.MARKET)
    entry_time = Column(DateTime, nullable=False)
    exit_time = Column(DateTime, nullable=True)
    entry_price = Column(Float, nullable=False)
    exit_price = Column(Float, nullable=True)
    size = Column(Float, nullable=False)
    pnl = Column(Float, nullable=True)
    pnl_pct = Column(Float, nullable=True)
    commission = Column(Float, default=0.0)
    slippage = Column(Float, default=0.0)
    status = Column(Enum(TradeStatus), default=TradeStatus.OPEN, nullable=False)
    regime = Column(String(32), nullable=True)
    notes = Column(Text, nullable=True)
    tags = Column(JSON, nullable=True, default=list)
    is_paper = Column(Boolean, default=True, nullable=False)
    external_order_id = Column(String(128), nullable=True)
    created_at = Column(DateTime, default=dt.datetime.utcnow)
    updated_at = Column(DateTime, default=dt.datetime.utcnow, onupdate=dt.datetime.utcnow)

    strategy = relationship("Strategy", back_populates="trades")
    asset = relationship("Asset", back_populates="trades")
    journal_entries = relationship("JournalEntry", back_populates="trade", cascade="all, delete-orphan")


# ── CONSENSUS SIGNALS ──────────────────────────────────────────

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


# ── DAILY P&L ───────────────────────────────────────────────────

class DailyPnL(Base):
    __tablename__ = "daily_pnl"
    __table_args__ = (UniqueConstraint("date", name="uix_daily_pnl_date"),)

    id = Column(Integer, primary_key=True)
    date = Column(Date, nullable=False, index=True)
    realized_pnl = Column(Float, default=0.0)
    unrealized_pnl = Column(Float, default=0.0)
    total_trades = Column(Integer, default=0)
    win_count = Column(Integer, default=0)
    loss_count = Column(Integer, default=0)
    gross_profit = Column(Float, default=0.0)
    gross_loss = Column(Float, default=0.0)


# ── JOURNAL ENTRIES ─────────────────────────────────────────────

class JournalEntry(Base):
    __tablename__ = "journal_entries"

    id = Column(Integer, primary_key=True)
    trade_id = Column(Integer, ForeignKey("trades.id"), nullable=True)
    entry_type = Column(String(32), default="note")  # note, pre_trade, post_trade, mistake, lesson
    content = Column(Text, nullable=False)
    mood = Column(String(32), nullable=True)
    mistakes = Column(JSON, nullable=True, default=list)
    lessons = Column(JSON, nullable=True, default=list)
    image_urls = Column(JSON, nullable=True, default=list)
    created_at = Column(DateTime, default=dt.datetime.utcnow)

    trade = relationship("Trade", back_populates="journal_entries")


# ── CALENDAR EVENTS ────────────────────────────────────────────

class CalendarEvent(Base):
    __tablename__ = "calendar_events"

    id = Column(Integer, primary_key=True)
    date = Column(Date, nullable=False, index=True)
    event_type = Column(String(32), default="trade_day")  # trade_day, economic_event, note
    title = Column(String(256), nullable=True)
    description = Column(Text, nullable=True)
    trade_ids = Column(JSON, nullable=True, default=list)
    pnl_summary = Column(Float, nullable=True)
    created_at = Column(DateTime, default=dt.datetime.utcnow)


# ── MARKET REGIMES ────────────────────────────────────────────

class MarketRegime(Base):
    __tablename__ = "market_regimes"
    __table_args__ = (UniqueConstraint("date", name="uix_regime_date"),)

    id = Column(Integer, primary_key=True)
    date = Column(Date, nullable=False, index=True)
    regime_label = Column(Enum(MarketRegimeLabel), nullable=True)
    volatility_regime = Column(String(16), nullable=True)  # low, normal, high
    trend_strength = Column(Float, nullable=True)
    confidence = Column(Float, nullable=True)
    features_json = Column(JSON, nullable=True)


# ── BROKER CONNECTIONS ──────────────────────────────────────────

class BrokerConnection(Base):
    __tablename__ = "broker_connections"
    __table_args__ = (UniqueConstraint("broker_name", "user_label", name="uix_broker_label"),)

    id = Column(Integer, primary_key=True)
    broker_name = Column(String(32), nullable=False, index=True)  # alpaca, binance, oanda, ibkr
    user_label = Column(String(64), nullable=True)
    api_key_encrypted = Column(Text, nullable=True)
    api_secret_encrypted = Column(Text, nullable=True)
    passphrase_encrypted = Column(Text, nullable=True)  # for some exchanges
    is_paper = Column(Boolean, default=True)
    is_active = Column(Boolean, default=True)
    extra_json = Column(JSON, nullable=True)  # additional config
    created_at = Column(DateTime, default=dt.datetime.utcnow)
    updated_at = Column(DateTime, default=dt.datetime.utcnow, onupdate=dt.datetime.utcnow)


# ── AGENT REPORTS ───────────────────────────────────────────────

class AgentReport(Base):
    __tablename__ = "agent_reports"

    id = Column(Integer, primary_key=True)
    agent_type = Column(String(32), nullable=False, index=True)
    timestamp = Column(DateTime, default=dt.datetime.utcnow, index=True)
    summary = Column(Text, nullable=False)
    bias_score = Column(Float, nullable=True)  # -100 to +100 or 0-100 depending on agent
    confidence = Column(Float, nullable=True)  # 0-100
    raw_data_json = Column(JSON, nullable=True)


# ── AGENT SIGNALS ───────────────────────────────────────────────

class AgentSignal(Base):
    __tablename__ = "agent_signals"
    __table_args__ = (Index("ix_agent_signal_active", "agent_type", "symbol", "expires_at"),)

    id = Column(Integer, primary_key=True)
    agent_type = Column(String(32), nullable=False, index=True)
    symbol = Column(String(32), nullable=True, index=True)
    signal = Column(String(16), nullable=False)  # bullish, bearish, neutral, halt
    strength = Column(Float, nullable=True)  # 0-1
    expires_at = Column(DateTime, nullable=True)
    created_at = Column(DateTime, default=dt.datetime.utcnow)


# ── NEWS SIGNALS ────────────────────────────────────────────────

class NewsSignal(Base):
    __tablename__ = "news_signals"
    __table_args__ = (Index("ix_news_time", "timestamp", "symbol"),)

    id = Column(Integer, primary_key=True)
    timestamp = Column(DateTime, default=dt.datetime.utcnow, index=True)
    symbol = Column(String(32), nullable=True, index=True)
    headline = Column(Text, nullable=True)
    sentiment_score = Column(Float, nullable=True)  # -1.0 to +1.0
    severity = Column(String(16), nullable=True)  # low, medium, high, critical
    source = Column(String(128), nullable=True)


# ── MODEL PERFORMANCE (SELF-LEARNING) ─────────────────────────

class ModelPerformance(Base):
    __tablename__ = "model_performance"
    __table_args__ = (
        UniqueConstraint("strategy_id", "regime", "param_hash", name="uix_model_perf"),
    )

    id = Column(Integer, primary_key=True)
    strategy_id = Column(Integer, ForeignKey("strategies.id"), nullable=False)
    regime = Column(String(32), nullable=False)
    param_hash = Column(String(64), nullable=False)
    win_rate = Column(Float, nullable=True)
    profit_factor = Column(Float, nullable=True)
    sharpe = Column(Float, nullable=True)
    expectancy = Column(Float, nullable=True)
    max_drawdown = Column(Float, nullable=True)
    sample_count = Column(Integer, default=0)
    last_updated = Column(DateTime, default=dt.datetime.utcnow, onupdate=dt.datetime.utcnow)
