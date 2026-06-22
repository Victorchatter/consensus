from __future__ import annotations

from typing import List, Optional
import datetime as dt
from fastapi import APIRouter, Depends, BackgroundTasks
from sqlalchemy.orm import Session

from app.core.database import get_db, SessionLocal
from app import models, schemas
from app.backtest.engine import BacktestEngine, ExecutionConfig
from app.backtest.optimization import ParameterGrid, run_grid_search, run_walk_forward, run_regime_aware_backtest
from app.backtest import BacktestBar
from app.data.feeders import get_feeder_for_source
from app.strategies.builtin import (
    SMACrossStrategy,
    RSIMeanReversionStrategy,
    BollingerBreakoutStrategy,
    MACDMomentumStrategy,
)

router = APIRouter(prefix="/backtest", tags=["backtest"])

STRATEGY_MAP = {
    "SMA Crossover": SMACrossStrategy,
    "RSI Mean Reversion": RSIMeanReversionStrategy,
    "Bollinger Bands Breakout": BollingerBreakoutStrategy,
    "MACD Momentum": MACDMomentumStrategy,
}


@router.post("/run", response_model=schemas.BacktestResult)
def run_backtest(
    payload: schemas.BacktestRequest,
    background_tasks: BackgroundTasks,
    db: Session = Depends(get_db),
):
    run = models.BacktestRun(
        strategy_id=payload.strategy_id,
        start_date=payload.start_date,
        end_date=payload.end_date,
        params=payload.params or {},
        status=models.BacktestStatus.PENDING,
    )
    db.add(run)
    db.commit()
    db.refresh(run)

    background_tasks.add_task(_execute_backtest, run.id, payload, db)

    return run


@router.get("/{run_id}", response_model=schemas.BacktestResult)
def get_backtest(run_id: int, db: Session = Depends(get_db)):
    run = db.query(models.BacktestRun).filter(models.BacktestRun.id == run_id).first()
    return run


@router.get("", response_model=List[schemas.BacktestResult])
def list_backtests(
    strategy_id: Optional[int] = None,
    db: Session = Depends(get_db),
):
    q = db.query(models.BacktestRun)
    if strategy_id:
        q = q.filter(models.BacktestRun.strategy_id == strategy_id)
    return q.order_by(models.BacktestRun.created_at.desc()).all()


def _try_load_bars(db: Session, asset_id: int, timeframe: str, start: dt.date, end: dt.date) -> int:
    """Fetch missing bars from the asset's data source and store them. Returns count inserted."""
    asset = db.query(models.Asset).filter(models.Asset.id == asset_id).first()
    if not asset:
        return 0
    feeder = get_feeder_for_source(asset.data_source or "yahoo")
    bars = feeder.fetch_historical(asset.symbol, start, end, timeframe)
    inserted = 0
    for bar in bars:
        existing = (
            db.query(models.PriceBar)
            .filter(
                models.PriceBar.asset_id == asset_id,
                models.PriceBar.timestamp == bar.timestamp,
                models.PriceBar.timeframe == timeframe,
            )
            .first()
        )
        if existing:
            existing.open = bar.open
            existing.high = bar.high
            existing.low = bar.low
            existing.close = bar.close
            existing.volume = bar.volume
        else:
            db.add(
                models.PriceBar(
                    asset_id=asset_id,
                    timestamp=bar.timestamp,
                    timeframe=timeframe,
                    open=bar.open,
                    high=bar.high,
                    low=bar.low,
                    close=bar.close,
                    volume=bar.volume,
                )
            )
            inserted += 1
    db.commit()
    return inserted


def _execute_backtest(run_id: int, payload: schemas.BacktestRequest, _db: Session):
    # Use a fresh session for the background task
    db = SessionLocal()
    try:
        # Fetch strategy
        strategy_db = db.query(models.Strategy).filter(models.Strategy.id == payload.strategy_id).first()
        if not strategy_db:
            _update_run(db, run_id, status="failed", error="Strategy not found")
            return

        strategy_cls = STRATEGY_MAP.get(strategy_db.name)
        if not strategy_cls:
            _update_run(db, run_id, status="failed", error=f"Strategy class not mapped: {strategy_db.name}")
            return

        strategy = strategy_cls(params=payload.params)

        # Fetch bars
        bars = (
            db.query(models.PriceBar)
            .filter(
                models.PriceBar.asset_id == payload.asset_id,
                models.PriceBar.timeframe == payload.timeframe,
                models.PriceBar.timestamp >= payload.start_date,
                models.PriceBar.timestamp <= payload.end_date,
            )
            .order_by(models.PriceBar.timestamp.asc())
            .all()
        )

        # Auto-fetch if insufficient bars
        if len(bars) < 50:
            inserted = _try_load_bars(db, payload.asset_id, payload.timeframe, payload.start_date, payload.end_date)
            print(f"[Backtest] Auto-fetched {inserted} bars for asset {payload.asset_id} ({payload.timeframe})")
            # Re-query after fetch
            bars = (
                db.query(models.PriceBar)
                .filter(
                    models.PriceBar.asset_id == payload.asset_id,
                    models.PriceBar.timeframe == payload.timeframe,
                    models.PriceBar.timestamp >= payload.start_date,
                    models.PriceBar.timestamp <= payload.end_date,
                )
                .order_by(models.PriceBar.timestamp.asc())
                .all()
            )

        if len(bars) < 50:
            _update_run(db, run_id, status="failed", error=f"Not enough bars: {len(bars)}. The data source may be unavailable or the symbol has no recent data.")
            return

        bt_bars = [
            BacktestBar(
                timestamp=b.timestamp,
                open=b.open,
                high=b.high,
                low=b.low,
                close=b.close,
                volume=b.volume or 0.0,
            )
            for b in bars
        ]

        config = ExecutionConfig(
            initial_cash=payload.initial_cash,
            commission_pct=payload.commission_pct,
        )
        engine = BacktestEngine(strategy, config)
        result = engine.run(bt_bars)

        _update_run(
            db,
            run_id,
            status="completed",
            metrics=result.metrics,
            equity_curve=result.equity_curve,
            trades=[
                {
                    "timestamp": t.timestamp.isoformat(),
                    "action": t.action,
                    "price": t.price,
                    "size": t.size,
                    "commission": t.commission,
                    "pnl": t.pnl,
                    "pnl_pct": t.pnl_pct,
                }
                for t in result.trades
            ],
        )
    except Exception as e:
        import traceback
        traceback.print_exc()
        _update_run(db, run_id, status="failed", error=str(e))
    finally:
        db.close()


def _update_run(db: Session, run_id: int, status: str, metrics=None, equity_curve=None, trades=None, error=None):
    run = db.query(models.BacktestRun).filter(models.BacktestRun.id == run_id).first()
    if not run:
        return
    run.status = status
    run.metrics_json = metrics
    run.equity_curve_json = equity_curve
    run.trades_json = trades
    run.error_message = error
    run.completed_at = dt.datetime.utcnow()
    db.commit()


# ── PARAMETER OPTIMIZATION ─────────────────────────────────────

@router.post("/optimize")
def optimize(
    strategy_id: int,
    asset_id: int,
    timeframe: str = "1d",
    grid: dict = {},
    metric: str = "sharpe_ratio",
    start_date: Optional[dt.date] = None,
    end_date: Optional[dt.date] = None,
    db: Session = Depends(get_db),
):
    strategy_db = db.query(models.Strategy).get(strategy_id)
    if not strategy_db:
        return {"error": "Strategy not found"}
    strategy_cls = STRATEGY_MAP.get(strategy_db.name)
    if not strategy_cls:
        return {"error": f"Strategy class not mapped: {strategy_db.name}"}

    asset = db.query(models.Asset).get(asset_id)
    if not asset:
        return {"error": "Asset not found"}

    end = end_date or dt.date.today()
    start = start_date or (end - dt.timedelta(days=365))

    bars = (
        db.query(models.PriceBar)
        .filter(
            models.PriceBar.asset_id == asset_id,
            models.PriceBar.timeframe == timeframe,
            models.PriceBar.timestamp >= start,
            models.PriceBar.timestamp <= end,
        )
        .order_by(models.PriceBar.timestamp.asc())
        .all()
    )
    if len(bars) < 50:
        return {"error": f"Not enough bars: {len(bars)}"}

    bt_bars = [
        BacktestBar(
            timestamp=b.timestamp,
            open=b.open,
            high=b.high,
            low=b.low,
            close=b.close,
            volume=b.volume or 0.0,
        )
        for b in bars
    ]

    # Asset-class aware commission defaults
    commission = 0.001 if asset.asset_class in ("stock", "etf") else 0.002 if asset.asset_class == "crypto" else 0.0003

    config = ExecutionConfig(commission_pct=commission)
    param_grid = ParameterGrid(params=grid)
    results = run_grid_search(strategy_cls, bt_bars, param_grid, config, metric)

    return {
        "strategy": strategy_db.name,
        "asset": asset.symbol,
        "metric": metric,
        "total_combinations": len(results),
        "best": results[0] if results else None,
        "top_5": results[:5],
    }


# ── WALK-FORWARD ANALYSIS ──────────────────────────────────────

@router.post("/walk-forward")
def walk_forward(
    strategy_id: int,
    asset_id: int,
    timeframe: str = "1d",
    grid: dict = {},
    train_size: int = 100,
    test_size: int = 30,
    metric: str = "sharpe_ratio",
    start_date: Optional[dt.date] = None,
    end_date: Optional[dt.date] = None,
    db: Session = Depends(get_db),
):
    strategy_db = db.query(models.Strategy).get(strategy_id)
    if not strategy_db:
        return {"error": "Strategy not found"}
    strategy_cls = STRATEGY_MAP.get(strategy_db.name)
    if not strategy_cls:
        return {"error": f"Strategy class not mapped: {strategy_db.name}"}

    asset = db.query(models.Asset).get(asset_id)
    if not asset:
        return {"error": "Asset not found"}

    end = end_date or dt.date.today()
    start = start_date or (end - dt.timedelta(days=730))

    bars = (
        db.query(models.PriceBar)
        .filter(
            models.PriceBar.asset_id == asset_id,
            models.PriceBar.timeframe == timeframe,
            models.PriceBar.timestamp >= start,
            models.PriceBar.timestamp <= end,
        )
        .order_by(models.PriceBar.timestamp.asc())
        .all()
    )
    if len(bars) < train_size + test_size + 10:
        return {"error": f"Not enough bars: {len(bars)}"}

    bt_bars = [
        BacktestBar(
            timestamp=b.timestamp,
            open=b.open,
            high=b.high,
            low=b.low,
            close=b.close,
            volume=b.volume or 0.0,
        )
        for b in bars
    ]

    commission = 0.001 if asset.asset_class in ("stock", "etf") else 0.002 if asset.asset_class == "crypto" else 0.0003
    config = ExecutionConfig(commission_pct=commission)
    param_grid = ParameterGrid(params=grid)

    result = run_walk_forward(strategy_cls, bt_bars, param_grid, train_size, test_size, config, metric)
    return {
        "strategy": strategy_db.name,
        "asset": asset.symbol,
        **result,
    }


# ── REGIME-AWARE BACKTEST ──────────────────────────────────────

@router.post("/regime-aware")
def regime_aware(
    strategy_id: int,
    asset_id: int,
    timeframe: str = "1d",
    regime_params: dict = {},
    start_date: Optional[dt.date] = None,
    end_date: Optional[dt.date] = None,
    db: Session = Depends(get_db),
):
    strategy_db = db.query(models.Strategy).get(strategy_id)
    if not strategy_db:
        return {"error": "Strategy not found"}
    strategy_cls = STRATEGY_MAP.get(strategy_db.name)
    if not strategy_cls:
        return {"error": f"Strategy class not mapped: {strategy_db.name}"}

    asset = db.query(models.Asset).get(asset_id)
    if not asset:
        return {"error": "Asset not found"}

    end = end_date or dt.date.today()
    start = start_date or (end - dt.timedelta(days=365))

    bars = (
        db.query(models.PriceBar)
        .filter(
            models.PriceBar.asset_id == asset_id,
            models.PriceBar.timeframe == timeframe,
            models.PriceBar.timestamp >= start,
            models.PriceBar.timestamp <= end,
        )
        .order_by(models.PriceBar.timestamp.asc())
        .all()
    )
    if len(bars) < 50:
        return {"error": f"Not enough bars: {len(bars)}"}

    bt_bars = [
        BacktestBar(
            timestamp=b.timestamp,
            open=b.open,
            high=b.high,
            low=b.low,
            close=b.close,
            volume=b.volume or 0.0,
        )
        for b in bars
    ]

    commission = 0.001 if asset.asset_class in ("stock", "etf") else 0.002 if asset.asset_class == "crypto" else 0.0003
    config = ExecutionConfig(commission_pct=commission)

    result = run_regime_aware_backtest(strategy_cls, bt_bars, regime_params, config)
    return {
        "strategy": strategy_db.name,
        "asset": asset.symbol,
        "metrics": result.metrics,
        "trades": len(result.trades),
        "regime_distribution": _regime_distribution(result.equity_curve),
    }


def _regime_distribution(equity_curve: list) -> dict:
    counts = {}
    for point in equity_curve:
        r = point.get("regime", "unknown")
        counts[r] = counts.get(r, 0) + 1
    total = sum(counts.values())
    return {k: round(v / total, 3) for k, v in counts.items()} if total else {}
