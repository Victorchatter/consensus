"""
Accuracy-derived voter weights (Section 5: weight by walk-forward hit rate, NOT
a hardcoded threshold).

Each voter earns its weight from its *own* realized directional accuracy over a
historical window: replay the bars through the voter, line every nonzero vote up
against what price actually did `horizon` bars later, and score the fraction it
called correctly. A coin-flipper (50%) earns weight 0; a perfect caller earns 1;
a consistently *wrong* voter is clamped to 0 rather than handed a negative
weight. This keeps the consensus aggregation a convex combination of edges
instead of trusting any single hardcoded number.

The mapping ``weight = max(0, 2*accuracy - 1)`` is the standard
"informedness"/Youden-style rescale of a hit rate onto [0, 1], where 0.5
(chance) maps to 0 and 1.0 maps to 1.
"""
from __future__ import annotations

from typing import Dict, List, Sequence

from app.consensus.base import Voter


def _sign(x: float) -> int:
    if x > 0:
        return 1
    if x < 0:
        return -1
    return 0


def compute_weights(
    voters: List[Voter],
    bars: Sequence,
    horizon: int = 1,
) -> Dict[str, float]:
    """Derive each voter's weight from its own walk-forward hit rate.

    For each voter: ``reset()``, then ``observe`` every bar in order, recording
    the vote emitted at index ``i``. The realized direction at ``i`` is
    ``sign(close[i + horizon] - close[i])``. Only nonzero votes that have a
    realized direction to compare against (``i + horizon`` in range) count.

        accuracy = (# nonzero votes where sign(vote) == realized) / (# scored)
        weight   = max(0.0, 2 * accuracy - 1)

    A voter that never casts a scored nonzero vote gets weight 0.0. If *every*
    voter ends up at 0.0, fall back to equal weights ({name: 1.0}) so the
    consensus is never degenerate (all-zero -> no trades).

    Args:
        voters: voters to score (anything with reset/observe and a .name).
        bars: ordered, Bar-like objects exposing at least ``.close``.
        horizon: how many bars ahead the realized direction is measured.

    Returns:
        One entry per voter name -> weight in [0, 1].
    """
    if horizon < 1:
        raise ValueError("horizon must be >= 1")

    closes = [float(b.close) for b in bars]
    n = len(closes)

    weights: Dict[str, float] = {}
    for voter in voters:
        voter.reset()
        correct = 0
        scored = 0
        for i in range(n):
            vote = int(voter.observe(bars[i]))
            if vote not in (-1, 0, 1):
                vote = 0
            # Only score nonzero votes that have a future bar to compare to.
            if vote == 0 or i + horizon >= n:
                continue
            realized = _sign(closes[i + horizon] - closes[i])
            scored += 1
            if vote == realized:
                correct += 1

        if scored == 0:
            weights[voter.name] = 0.0
            continue
        accuracy = correct / scored
        weights[voter.name] = max(0.0, 2.0 * accuracy - 1.0)

    if all(w == 0.0 for w in weights.values()):
        return {name: 1.0 for name in weights}

    return weights


__all__ = ["compute_weights"]
