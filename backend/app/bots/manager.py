from __future__ import annotations

import uuid
from typing import Dict, Optional, Any, List

from app.bots.bot import TradingBot, BotConfig
from app.core.database import SessionLocal
from app import models


class BotManager:
    """Manages a collection of trading bots."""

    def __init__(self):
        self._bots: Dict[str, TradingBot] = {}

    def _get_db(self):
        return SessionLocal()

    def create_bot(self, config: BotConfig) -> Optional[TradingBot]:
        db = self._get_db()
        try:
            strategy = db.query(models.Strategy).get(config.strategy_id)
            if not strategy:
                return None
            # Dynamically load strategy class from dot-separated path
            # e.g. "app.strategies.builtin.macd.MACDMomentumStrategy"
            if ":" in strategy.class_path:
                module_path, class_name = strategy.class_path.rsplit(":", 1)
            else:
                module_path, class_name = strategy.class_path.rsplit(".", 1)
            import importlib
            mod = importlib.import_module(module_path)
            strategy_class = getattr(mod, class_name)
            bot = TradingBot(config, strategy_class, SessionLocal)
            self._bots[config.id] = bot
            return bot
        except Exception as e:
            print(f"[BotManager] Failed to create bot: {e}")
            import traceback
            traceback.print_exc()
            return None
        finally:
            db.close()

    async def start_bot(self, bot_id: str) -> bool:
        bot = self._bots.get(bot_id)
        if not bot:
            return False
        await bot.start()
        return True

    async def stop_bot(self, bot_id: str) -> bool:
        bot = self._bots.get(bot_id)
        if not bot:
            return False
        await bot.stop()
        return True

    def get_bot(self, bot_id: str) -> Optional[TradingBot]:
        return self._bots.get(bot_id)

    def list_bots(self) -> List[Dict[str, Any]]:
        return [bot.get_state() for bot in self._bots.values()]

    def delete_bot(self, bot_id: str) -> bool:
        bot = self._bots.pop(bot_id, None)
        if bot:
            if bot.config.active:
                import asyncio
                asyncio.create_task(bot.stop())
            return True
        return False


# Global singleton
manager = BotManager()
