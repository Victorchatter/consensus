"""Lightweight quote poller that fetches latest prices from Yahoo Finance
and stores them in the Quote table so the frontend polling fallback works.

Runs as a background task in the FastAPI lifespan.
No external API keys required.
"""
from __future__ import annotations

import asyncio
import datetime as dt
from typing import Optional

from app.core.database import SessionLocal
from app import models
from app.data.feeders import get_feeder_for_source


class QuotePoller:
    """Fetches the most recent daily bar for each active asset and stores
    it as a Quote row.  This gives the frontend a 'live-ish' price to poll
    when the Alpaca WebSocket is unavailable.
    """

    def __init__(self, interval_sec: int = 30):
        self.interval_sec = interval_sec
        self._running = False
        self._task: Optional[asyncio.Task] = None

    async def start(self):
        if self._running:
            return
        self._running = True
        self._task = asyncio.create_task(self._loop())
        print("[QuotePoller] Started")

    async def stop(self):
        self._running = False
        if self._task:
            self._task.cancel()
            try:
                await self._task
            except asyncio.CancelledError:
                pass
            self._task = None
        print("[QuotePoller] Stopped")

    async def _loop(self):
        while self._running:
            try:
                await asyncio.to_thread(self._tick)
            except Exception as e:
                print(f"[QuotePoller] Tick error: {e}")
            await asyncio.sleep(self.interval_sec)

    def _tick(self):
        db = SessionLocal()
        try:
            assets = db.query(models.Asset).filter(models.Asset.is_active == True).all()
            today = dt.date.today()
            yesterday = today - dt.timedelta(days=7)

            for asset in assets:
                try:
                    # Fetch the last few daily bars from Yahoo Finance
                    feeder = get_feeder_for_source(asset.data_source or "yahoo")
                    bars = feeder.fetch_historical(asset.symbol, yesterday, today, "1d")
                    if not bars:
                        continue

                    latest = bars[-1]
                    # Upsert quote
                    quote = (
                        db.query(models.Quote)
                        .filter(models.Quote.asset_id == asset.id)
                        .order_by(models.Quote.timestamp.desc())
                        .first()
                    )
                    if quote and quote.timestamp == latest.timestamp:
                        # Same bar — update price in case it moved (intraday)
                        quote.last_price = latest.close
                        quote.volume = latest.volume
                    else:
                        db.add(
                            models.Quote(
                                asset_id=asset.id,
                                timestamp=latest.timestamp,
                                last_price=latest.close,
                                volume=latest.volume,
                            )
                        )
                except Exception as e:
                    print(f"[QuotePoller] Failed for {asset.symbol}: {e}")
            db.commit()
        finally:
            db.close()
