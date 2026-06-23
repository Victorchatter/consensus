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
