"""
MonteCarloVoter: a bootstrap Monte-Carlo directional voter.

The voter keeps a rolling window of the most recent `lookback` log-returns.
Once warm, on every bar it bootstrap-resamples those historical returns to
build `n_paths` cumulative forward paths of length `horizon`, then votes on the
fraction of paths that finished above the starting price.

Determinism: the RNG is created ONCE in reset() (seeded from `seed`) and is
never reseeded per bar. Because the same bars produce the same observe() calls
in the same order, the same draws come out in the same order, so identical
bars + seed => identical vote sequence across runs.
"""
from __future__ import annotations

import math
from collections import deque
from typing import Deque, Optional

import numpy as np

from app.consensus.base import Voter
from app.strategies import Bar


class MonteCarloVoter(Voter):
    """Bootstrap Monte-Carlo voter over recent log-returns.

    Params
    ------
    lookback : rolling window of log-returns to resample from (warm-up length).
    horizon  : number of forward steps per simulated path.
    n_paths  : number of bootstrap paths per observation.
    up_quantile : decision band; vote +1 if frac_up > up_quantile,
                  -1 if frac_up < 1 - up_quantile, else 0.
    seed     : RNG seed (deterministic).
    """

    name = "montecarlo"

    def __init__(
        self,
        lookback: int = 200,
        horizon: int = 12,
        n_paths: int = 400,
        up_quantile: float = 0.55,
        seed: int = 0,
        weight: float = 1.0,
    ):
        self.lookback = int(lookback)
        self.horizon = int(horizon)
        self.n_paths = int(n_paths)
        self.up_quantile = float(up_quantile)
        self.seed = int(seed)
        self.weight = float(weight)

        self._returns: Deque[float] = deque(maxlen=self.lookback)
        self._prev_close: Optional[float] = None
        self._rng = np.random.default_rng(self.seed)

    def reset(self) -> None:
        self._returns = deque(maxlen=self.lookback)
        self._prev_close = None
        # Create the RNG once here; never reseed per bar.
        self._rng = np.random.default_rng(self.seed)

    def observe(self, bar: Bar) -> int:
        close = float(bar.close)

        # Accumulate log-returns; first bar only seeds prev_close.
        if self._prev_close is not None and self._prev_close > 0.0 and close > 0.0:
            self._returns.append(math.log(close / self._prev_close))
        self._prev_close = close

        # Until the window is full, abstain.
        if len(self._returns) < self.lookback:
            return 0

        hist = np.asarray(self._returns, dtype=np.float64)

        # Bootstrap-resample returns -> (n_paths, horizon) draws, then take the
        # cumulative sum of log-returns along each path. The terminal cumulative
        # log-return > 0 iff the path's price finished above the start price.
        draws = self._rng.choice(hist, size=(self.n_paths, self.horizon), replace=True)
        terminal = draws.sum(axis=1)
        frac_up = float(np.count_nonzero(terminal > 0.0)) / self.n_paths

        if frac_up > self.up_quantile:
            return 1
        if frac_up < (1.0 - self.up_quantile):
            return -1
        return 0
