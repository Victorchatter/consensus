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


def test_daily_pnl_rebaselines_each_utc_day():
    import datetime as dt
    b = _bot()
    d1a = dt.datetime(2026, 1, 1, 10, 0)
    d1b = dt.datetime(2026, 1, 1, 15, 0)
    d2 = dt.datetime(2026, 1, 2, 9, 0)
    assert b._daily_pnl(100_000, d1a) == 0.0       # first call today -> baseline set
    assert b._daily_pnl(98_000, d1b) == -2000.0    # down 2k same day
    assert b._daily_pnl(98_000, d2) == 0.0         # new UTC day -> re-baseline, no carry-over


def test_ensure_daily_baseline_snapshots_without_signal():
    import datetime as dt
    b = _bot()

    class _Acct:
        equity = 50_000.0
        balance = 50_000.0

    class _Conn:
        def get_account(self):
            return _Acct()

    b._connector = _Conn()
    b._ensure_daily_baseline(dt.datetime(2026, 3, 1, 0, 5))
    assert b._daily_baseline_date == dt.date(2026, 3, 1)
    assert b._daily_baseline_equity == 50_000.0
    # a loss that happens before the day's first signal is now measured correctly
    assert b._daily_pnl(48_000.0, dt.datetime(2026, 3, 1, 9, 0)) == -2000.0
