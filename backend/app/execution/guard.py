"""Execution-layer risk guard. Enforced outside the strategy: the bot consults
it before every order, so a strategy bug cannot bypass the kill-switch."""
from __future__ import annotations

import datetime as dt
from typing import Optional


class RiskGuard:
    def __init__(self, max_daily_loss_pct: float, max_position_pct: float):
        self.max_daily_loss_pct = max_daily_loss_pct
        self.max_position_pct = max_position_pct
        self.latched = False
        self._latched_date: Optional[dt.date] = None

    def reset(self) -> None:
        self.latched = False
        self._latched_date = None

    def check(self, is_reducing: bool, intended_value: float, equity: float,
              daily_pnl: float, now: dt.datetime) -> tuple[bool, str]:
        today = now.date()
        # Auto-reset latch at UTC day rollover.
        if self.latched and self._latched_date is not None and today > self._latched_date:
            self.reset()

        # Latch on daily-loss breach (engages even on a reducing order's check).
        if daily_pnl <= -abs(equity) * self.max_daily_loss_pct:
            if not self.latched:
                self.latched = True
                self._latched_date = today

        if is_reducing:
            return True, "ok (reducing)"

        if self.latched:
            return False, f"kill-switch latched (daily loss breach on {self._latched_date})"

        if intended_value > abs(equity) * self.max_position_pct:
            return False, (f"position cap: {intended_value:.2f} > "
                           f"{self.max_position_pct:.0%} of equity {equity:.2f}")
        return True, "ok"
