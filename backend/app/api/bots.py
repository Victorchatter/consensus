from __future__ import annotations

from typing import List, Optional
from fastapi import APIRouter
from pydantic import BaseModel

from app.bots.manager import manager
from app.bots.bot import BotConfig

router = APIRouter(prefix="/bots", tags=["bots"])


class BotCreateRequest(BaseModel):
    name: str
    strategy_id: int
    asset_ids: List[int]
    timeframe: str = "1d"
    data_source: str = "yahoo"
    broker: str = "paper"
    mode: str = "paper"
    broker_connection_id: Optional[int] = None
    initial_cash: float = 100_000.0
    max_hold_minutes: int = 120
    close_before_market_close: bool = True


class BotUpdateRequest(BaseModel):
    name: Optional[str] = None
    active: Optional[bool] = None


@router.post("")
def create_bot(payload: BotCreateRequest):
    import uuid
    config = BotConfig(
        id=str(uuid.uuid4())[:8],
        name=payload.name,
        strategy_id=payload.strategy_id,
        asset_ids=payload.asset_ids,
        timeframe=payload.timeframe,
        data_source=payload.data_source,
        broker=payload.broker,
        mode=payload.mode,
        broker_connection_id=payload.broker_connection_id,
        initial_cash=payload.initial_cash,
        max_hold_minutes=payload.max_hold_minutes,
        close_before_market_close=payload.close_before_market_close,
    )
    bot = manager.create_bot(config)
    if not bot:
        return {"error": "Failed to create bot — strategy not found or invalid"}
    return bot.get_state()


@router.get("")
def list_bots():
    return manager.list_bots()


@router.get("/{bot_id}")
def get_bot(bot_id: str):
    bot = manager.get_bot(bot_id)
    if not bot:
        return {"error": "Bot not found"}
    return bot.get_state()


@router.post("/{bot_id}/start")
async def start_bot(bot_id: str):
    ok = await manager.start_bot(bot_id)
    if not ok:
        return {"error": "Bot not found"}
    bot = manager.get_bot(bot_id)
    return bot.get_state() if bot else {"error": "Bot not found"}


@router.post("/{bot_id}/confirm-live")
def confirm_live(bot_id: str):
    """Explicit user confirmation required before a live-mode bot places real orders."""
    bot = manager.get_bot(bot_id)
    if not bot:
        return {"error": "Bot not found"}
    if bot.config.mode != "live":
        return {"error": "Bot is not in live mode"}
    bot.confirm_live()
    return {"confirmed": True, "mode": "live", "bot_id": bot_id}


@router.post("/{bot_id}/stop")
async def stop_bot(bot_id: str):
    ok = await manager.stop_bot(bot_id)
    if not ok:
        return {"error": "Bot not found"}
    bot = manager.get_bot(bot_id)
    return bot.get_state() if bot else {"error": "Bot not found"}


@router.delete("/{bot_id}")
def delete_bot(bot_id: str):
    ok = manager.delete_bot(bot_id)
    if not ok:
        return {"error": "Bot not found"}
    return {"deleted": True}
