"""
Position sizing: fractional Kelly with a hard cap.

Section 1 safety rule — the returned fraction MUST NEVER exceed `cap`,
regardless of how large the raw Kelly edge is. The cap is the last line of
defence against an over-confident edge estimate blowing up the bankroll.

Everything here is pure: no I/O, no state. Functions take primitives and a
list of realised trade PnLs and return a single position fraction in [0, cap].
"""
from __future__ import annotations

from typing import List


def kelly_fraction(
    win_rate: float,
    win_loss_ratio: float,
    fraction: float = 0.25,
    cap: float = 0.20,
) -> float:
    """Fractional Kelly sizing, hard-capped.

    full Kelly = win_rate - (1 - win_rate) / win_loss_ratio
    sized      = max(0, fraction * full)            (never bet a negative edge)
    return       min(cap, sized)                    (Section 1: never exceed cap)

    A non-positive `win_loss_ratio` is meaningless (no payoff per unit risk),
    so we abstain by returning 0.0 rather than dividing by zero.
    """
    if win_loss_ratio <= 0:
        return 0.0
    full = win_rate - (1.0 - win_rate) / win_loss_ratio
    sized = max(0.0, fraction * full)
    return min(cap, sized)


def kelly_from_trades(
    pnls: List[float],
    fraction: float = 0.25,
    cap: float = 0.20,
) -> float:
    """Derive win_rate and win/loss ratio from realised trade PnLs, then size.

    win_rate        = #wins / #trades
    win_loss_ratio  = avg(win magnitude) / avg(loss magnitude)

    Degenerate inputs are handled without dividing by zero:
      * empty list           -> 0.0 (no information)
      * all wins / no losses -> no downside estimate, abstain with 0.0
      * all losses / no wins -> win_rate 0 -> non-positive edge -> 0.0
    PnLs of exactly 0.0 are treated as non-wins and contribute no magnitude.
    """
    n = len(pnls)
    if n == 0:
        return 0.0

    wins = [p for p in pnls if p > 0]
    losses = [p for p in pnls if p < 0]

    win_rate = len(wins) / n

    # No losing trades means we cannot estimate the downside leg of the ratio.
    # Refuse to size off an undefined risk rather than assume infinite edge.
    if not losses:
        return 0.0
    # No wins -> zero numerator -> ratio 0 -> kelly_fraction abstains anyway,
    # but short-circuit to keep the ratio well-defined.
    if not wins:
        return 0.0

    avg_win = sum(wins) / len(wins)
    avg_loss = sum(abs(p) for p in losses) / len(losses)
    if avg_loss == 0:
        return 0.0

    win_loss_ratio = avg_win / avg_loss
    return kelly_fraction(win_rate, win_loss_ratio, fraction=fraction, cap=cap)
