from __future__ import annotations

import datetime as dt
from typing import Optional, List
from pydantic import BaseModel, ConfigDict, Field


# ── ASSET SCHEMAS ───────────────────────────────────────────────

class AssetBase(BaseModel):
    symbol: str = Field(..., max_length=32)
    name: Optional[str] = None
    asset_class: str = "stock"
    exchange: Optional[str] = None
    data_source: Optional[str] = "yahoo"
    is_active: bool = True


class AssetCreate(AssetBase):
    pass


class AssetRead(AssetBase):
    model_config = ConfigDict(from_attributes=True)
    id: int
    created_at: Optional[dt.datetime] = None


# ── PRICE BAR SCHEMAS ──────────────────────────────────────────

class PriceBarRead(BaseModel):
    model_config = ConfigDict(from_attributes=True)
    timestamp: dt.datetime
    timeframe: str
    open: float
    high: float
    low: float
    close: float
    volume: Optional[float] = None


# ── QUOTE SCHEMAS ─────────────────────────────────────────────

class QuoteRead(BaseModel):
    model_config = ConfigDict(from_attributes=True)
    timestamp: dt.datetime
    bid: Optional[float] = None
    ask: Optional[float] = None
    last_price: float
    volume: Optional[float] = None


# ── TRADE SCHEMAS ────────────────────────────────────────────

class TradeBase(BaseModel):
    asset_id: int
    direction: str  # long / short
    order_type: str = "market"
    entry_price: float
    size: float
    notes: Optional[str] = None
    tags: Optional[List[str]] = None
    is_paper: bool = True


class TradeCreate(TradeBase):
    strategy_id: Optional[int] = None
    regime: Optional[str] = None


class TradeUpdate(BaseModel):
    exit_price: Optional[float] = None
    exit_time: Optional[dt.datetime] = None
    status: Optional[str] = None
    pnl: Optional[float] = None
    pnl_pct: Optional[float] = None
    notes: Optional[str] = None
    tags: Optional[List[str]] = None


class TradeRead(TradeBase):
    model_config = ConfigDict(from_attributes=True)
    id: int
    strategy_id: Optional[int] = None
    asset: Optional[AssetRead] = None
    entry_time: dt.datetime
    exit_time: Optional[dt.datetime] = None
    exit_price: Optional[float] = None
    pnl: Optional[float] = None
    pnl_pct: Optional[float] = None
    commission: float = 0.0
    slippage: float = 0.0
    status: str
    regime: Optional[str] = None
    external_order_id: Optional[str] = None
    created_at: Optional[dt.datetime] = None
    updated_at: Optional[dt.datetime] = None


# ── JOURNAL SCHEMAS ───────────────────────────────────────────

class JournalEntryBase(BaseModel):
    entry_type: str = "note"
    content: str
    mood: Optional[str] = None
    mistakes: Optional[List[str]] = None
    lessons: Optional[List[str]] = None
    image_urls: Optional[List[str]] = None


class JournalEntryCreate(JournalEntryBase):
    trade_id: Optional[int] = None


class JournalEntryUpdate(BaseModel):
    entry_type: Optional[str] = None
    content: Optional[str] = None
    mood: Optional[str] = None
    mistakes: Optional[List[str]] = None
    lessons: Optional[List[str]] = None
    image_urls: Optional[List[str]] = None
    trade_id: Optional[int] = None


class JournalEntryRead(JournalEntryBase):
    model_config = ConfigDict(from_attributes=True)
    id: int
    trade_id: Optional[int] = None
    created_at: Optional[dt.datetime] = None


# ── STRATEGY SCHEMAS ──────────────────────────────────────────

class StrategyBase(BaseModel):
    name: str
    class_path: str
    params_schema: Optional[dict] = None
    description: Optional[str] = None
    is_active: bool = True


class StrategyCreate(StrategyBase):
    pass


class StrategyRead(StrategyBase):
    model_config = ConfigDict(from_attributes=True)
    id: int
    is_builtin: bool = True
    created_at: Optional[dt.datetime] = None


# ── BACKTEST SCHEMAS ────────────────────────────────────────

class BacktestRequest(BaseModel):
    strategy_id: int
    asset_id: int
    start_date: dt.date
    end_date: dt.date
    params: Optional[dict] = None
    timeframe: str = "1d"
    initial_cash: float = 100_000.0
    commission_pct: float = 0.001


class BacktestMetrics(BaseModel):
    total_return: float
    cagr: float
    sharpe_ratio: float
    sortino_ratio: Optional[float] = None
    max_drawdown: float
    win_rate: float
    profit_factor: float
    expectancy: float
    total_trades: int
    avg_trade: float
    avg_win: float
    avg_loss: float


class BacktestResult(BaseModel):
    """Backtest result. Field names match SQLAlchemy model columns exactly
    (metrics_json, equity_curve_json, trades_json) so from_attributes works."""
    model_config = ConfigDict(from_attributes=True)
    id: int
    strategy_id: int
    status: str
    params: Optional[dict] = None
    metrics_json: Optional[dict] = None
    equity_curve_json: Optional[List[dict]] = None
    trades_json: Optional[List[dict]] = None
    error_message: Optional[str] = None
    created_at: Optional[dt.datetime] = None
    completed_at: Optional[dt.datetime] = None


# ── CALENDAR SCHEMAS ────────────────────────────────────────

class CalendarEventCreate(BaseModel):
    date: dt.date
    event_type: str
    title: Optional[str] = None
    description: Optional[str] = None
    trade_ids: Optional[List[int]] = None
    pnl_summary: Optional[float] = None


class CalendarEventRead(CalendarEventCreate):
    model_config = ConfigDict(from_attributes=True)
    id: int


# ── DAILY P&L SCHEMAS ───────────────────────────────────────

class DailyPnLRead(BaseModel):
    model_config = ConfigDict(from_attributes=True)
    id: int
    date: dt.date
    realized_pnl: float
    unrealized_pnl: float
    total_trades: int
    win_count: int
    loss_count: int
    gross_profit: float
    gross_loss: float


# ── PERFORMANCE SUMMARY ───────────────────────────────────────

class PerformanceSummary(BaseModel):
    total_trades: int
    win_count: int
    loss_count: int
    win_rate: float
    profit_factor: float
    sharpe_ratio: Optional[float] = None
    max_drawdown: float
    total_pnl: float
    avg_trade_pnl: float
    best_trade: Optional[float] = None
    worst_trade: Optional[float] = None
