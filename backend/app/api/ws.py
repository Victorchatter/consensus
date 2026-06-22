from __future__ import annotations

import asyncio
import json
from fastapi import APIRouter, WebSocket, WebSocketDisconnect

from app.data.ws_manager import manager, Tick

router = APIRouter()


def _tick_to_json(tick: Tick) -> dict:
    return {
        "type": "tick",
        "symbol": tick.symbol,
        "timestamp": tick.timestamp.isoformat(),
        "price": tick.price,
        "bid": tick.bid,
        "ask": tick.ask,
        "volume": tick.volume,
    }


@router.websocket("/ws/market-data")
async def market_data_ws(websocket: WebSocket):
    await websocket.accept()
    queue = manager.register_client()
    subscribed_symbols: set = set()

    # Send current snapshot
    snapshot = {
        "type": "snapshot",
        "prices": {
            sym: {"price": t.price, "bid": t.bid, "ask": t.ask}
            for sym, t in manager._latest.items()
        },
    }
    await websocket.send_json(snapshot)

    async def reader():
        while True:
            try:
                msg = await websocket.receive_json()
                action = msg.get("action")
                symbols = msg.get("symbols", [])
                if action == "subscribe" and symbols:
                    subscribed_symbols.update(symbols)
                    await manager.subscribe_symbols(list(subscribed_symbols))
                elif action == "unsubscribe" and symbols:
                    for s in symbols:
                        subscribed_symbols.discard(s)
            except Exception:
                break

    async def writer():
        while True:
            try:
                tick = await asyncio.wait_for(queue.get(), timeout=30.0)
                if not subscribed_symbols or tick.symbol in subscribed_symbols:
                    await websocket.send_json(_tick_to_json(tick))
            except asyncio.TimeoutError:
                # Send heartbeat to keep connection alive
                await websocket.send_json({"type": "heartbeat"})
            except Exception:
                break

    try:
        await asyncio.gather(reader(), writer())
    except WebSocketDisconnect:
        pass
    finally:
        manager.unregister_client(queue)
