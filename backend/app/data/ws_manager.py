from __future__ import annotations

import asyncio
import json
import datetime as dt
from typing import Dict, List, Set, Optional
from dataclasses import dataclass

from app.core.config import settings

# Lazy import websockets — may fail on some installs
_websockets = None

def _get_websockets():
    global _websockets
    if _websockets is None:
        try:
            import websockets
            _websockets = websockets
        except Exception as e:
            print(f"[WARN] websockets not available: {e}")
            _websockets = False
    return _websockets


@dataclass
class Tick:
    symbol: str
    timestamp: dt.datetime
    price: float
    bid: Optional[float] = None
    ask: Optional[float] = None
    volume: Optional[float] = None
    exchange: Optional[str] = None


class AlpacaWebSocketFeed:
    """Connects to Alpaca Data WebSocket for real-time stock quotes."""

    URL = "wss://stream.data.alpaca.markets/v2/iex"

    def __init__(self):
        self.ws = None
        self.subscribed: Set[str] = set()
        self.running = False
        self._listeners: List[callable] = []
        self._reconnect_delay = 1.0

    def add_listener(self, callback: callable):
        self._listeners.append(callback)

    def remove_listener(self, callback: callable):
        if callback in self._listeners:
            self._listeners.remove(callback)

    async def _notify(self, tick: Tick):
        for cb in self._listeners:
            try:
                cb(tick)
            except Exception:
                pass

    async def connect(self):
        ws_mod = _get_websockets()
        if not ws_mod:
            print("[AlpacaWS] websockets library not installed. Skipping real-time feed.")
            return
        if not settings.alpaca_api_key:
            print("[AlpacaWS] No API key configured. Skipping real-time feed.")
            return
        self.running = True
        while self.running:
            try:
                print(f"[AlpacaWS] Connecting to {self.URL}...")
                self.ws = await ws_mod.connect(self.URL)
                auth_msg = {
                    "action": "auth",
                    "key": settings.alpaca_api_key,
                    "secret": settings.alpaca_secret_key,
                }
                await self.ws.send(json.dumps(auth_msg))
                resp = await self.ws.recv()
                print(f"[AlpacaWS] Auth response: {resp}")

                if self.subscribed:
                    await self._send_subscribe(list(self.subscribed))

                self._reconnect_delay = 1.0
                await self._read_loop()
            except Exception as e:
                print(f"[AlpacaWS] Error: {e}. Reconnecting in {self._reconnect_delay}s...")
                await asyncio.sleep(self._reconnect_delay)
                self._reconnect_delay = min(self._reconnect_delay * 2, 60)

    async def _read_loop(self):
        async for message in self.ws:
            if not self.running:
                break
            try:
                data = json.loads(message)
                for item in data:
                    if item.get("T") == "q":
                        tick = Tick(
                            symbol=item.get("S", ""),
                            timestamp=dt.datetime.utcnow(),
                            price=(item.get("ap", 0) + item.get("bp", 0)) / 2 if item.get("ap") and item.get("bp") else item.get("ap", item.get("bp", 0)),
                            bid=item.get("bp"),
                            ask=item.get("ap"),
                            exchange=item.get("x"),
                        )
                        await self._notify(tick)
                    elif item.get("T") == "t":
                        tick = Tick(
                            symbol=item.get("S", ""),
                            timestamp=dt.datetime.utcnow(),
                            price=item.get("p", 0),
                            volume=item.get("v", 0),
                            exchange=item.get("x"),
                        )
                        await self._notify(tick)
            except Exception as e:
                print(f"[AlpacaWS] Parse error: {e}")

    async def subscribe(self, symbols: List[str]):
        new = [s for s in symbols if s not in self.subscribed]
        if not new:
            return
        self.subscribed.update(new)
        if self.ws and hasattr(self.ws, 'open') and self.ws.open:
            await self._send_subscribe(new)

    async def _send_subscribe(self, symbols: List[str]):
        msg = {"action": "subscribe", "quotes": symbols}
        await self.ws.send(json.dumps(msg))
        print(f"[AlpacaWS] Subscribed: {symbols}")

    async def disconnect(self):
        self.running = False
        if self.ws:
            await self.ws.close()


class MarketDataManager:
    def __init__(self):
        self.alpaca = AlpacaWebSocketFeed()
        self.alpaca.add_listener(self._on_tick)
        self._clients: List[asyncio.Queue] = []
        self._latest: Dict[str, Tick] = {}
        self._running = False

    def _on_tick(self, tick: Tick):
        self._latest[tick.symbol] = tick
        for queue in self._clients:
            try:
                queue.put_nowait(tick)
            except asyncio.QueueFull:
                pass

    async def start(self):
        self._running = True
        await self.alpaca.connect()

    async def stop(self):
        self._running = False
        await self.alpaca.disconnect()

    def register_client(self) -> asyncio.Queue:
        queue: asyncio.Queue = asyncio.Queue(maxsize=100)
        self._clients.append(queue)
        return queue

    def unregister_client(self, queue: asyncio.Queue):
        if queue in self._clients:
            self._clients.remove(queue)

    async def subscribe_symbols(self, symbols: List[str]):
        await self.alpaca.subscribe(symbols)

    def get_latest(self, symbol: str) -> Optional[Tick]:
        return self._latest.get(symbol)


# Global singleton
manager = MarketDataManager()
