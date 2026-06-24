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
