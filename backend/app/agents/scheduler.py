from __future__ import annotations

import asyncio
import datetime as dt
from typing import Optional

from app.agents.news_prodigy import NewsProdigy
from app.agents.financial_analyst import FinancialMarketAnalyst
from app.agents.economic_analyst import EconomicAnalyst
from app.agents.political_analyst import PoliticalAnalyst
from app.agents.ceo_agent import CEOAgent


class AgentScheduler:
    """Runs the agent swarm on a schedule in the background.

    Sub-agents are pure data gatherers and run frequently.
    CEO agent is the sole qualitative analyzer + trade executor and runs
    every 4 hours (with paperclip-style heartbeat check-ins).

    CRITICAL: All agent .run() calls are wrapped in asyncio.to_thread()
    so synchronous network I/O (RSS fetching, web searches) does NOT block
    the FastAPI event loop and render the API unresponsive.
    """

    def __init__(self):
        self._running = False
        self._task: Optional[asyncio.Task] = None
        self._last_run: dict[str, dt.datetime] = {}

    async def start(self):
        if self._running:
            return
        self._running = True
        self._task = asyncio.create_task(self._loop())

    async def stop(self):
        self._running = False
        if self._task:
            self._task.cancel()
            try:
                await self._task
            except asyncio.CancelledError:
                pass
            self._task = None

    async def _loop(self):
        while self._running:
            now = dt.datetime.utcnow()
            try:
                # News Prodigy: every 5 minutes
                if self._should_run("news_prodigy", now, minutes=5):
                    await asyncio.to_thread(NewsProdigy().run)
                    self._last_run["news_prodigy"] = now

                # Financial Analyst: every 15 minutes
                if self._should_run("financial_analyst", now, minutes=15):
                    await asyncio.to_thread(FinancialMarketAnalyst().run)
                    self._last_run["financial_analyst"] = now

                # Economic Analyst: every 6 hours
                if self._should_run("economic_analyst", now, hours=6):
                    await asyncio.to_thread(EconomicAnalyst().run)
                    self._last_run["economic_analyst"] = now

                # Political Analyst: every 4 hours
                if self._should_run("political_analyst", now, hours=4):
                    await asyncio.to_thread(PoliticalAnalyst().run)
                    self._last_run["political_analyst"] = now

                # CEO Agent: every 4 hours (paperclip heartbeat + full cycle)
                if self._should_run("ceo_agent", now, hours=4):
                    await asyncio.to_thread(CEOAgent().run)
                    self._last_run["ceo_agent"] = now

            except Exception as e:
                print(f"[AgentScheduler] Error: {e}")
                import traceback
                traceback.print_exc()

            await asyncio.sleep(60)

    def _should_run(
        self,
        name: str,
        now: dt.datetime,
        minutes: int = 0,
        hours: int = 0,
        days: int = 0,
        at_hour: Optional[int] = None,
        at_hours: Optional[list[int]] = None,
        at_weekday: Optional[int] = None,
    ) -> bool:
        last = self._last_run.get(name)
        if not last:
            if at_hour is not None and now.hour != at_hour:
                return False
            if at_hours is not None and now.hour not in at_hours:
                return False
            if at_weekday is not None and now.weekday() != at_weekday:
                return False
            return True

        delta = now - last
        if minutes and delta >= dt.timedelta(minutes=minutes):
            return True
        if hours and delta >= dt.timedelta(hours=hours):
            if at_hour is not None and now.hour != at_hour:
                return False
            if at_hours is not None and now.hour not in at_hours:
                return False
            return True
        if days and delta >= dt.timedelta(days=days):
            if at_weekday is not None and now.weekday() != at_weekday:
                return False
            if at_hour is not None and now.hour != at_hour:
                return False
            return True
        return False


# Global scheduler instance
scheduler = AgentScheduler()
