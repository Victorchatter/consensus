"""
Concrete, independent statistical voters for the consensus engine.

Each voter is a small, *incremental* `Voter` subclass: `observe(bar)` updates an
O(1)/O(window) rolling state and returns a directional vote in {-1, 0, +1}.
There is no look-ahead and no O(n^2) recompute — a full backtest stays O(n) per
voter. Memory is bounded: a voter only retains the rolling window it needs.

The voters are deliberately *diverse* (trend, mean-reversion, breakout, regime
filter) so the weighted consensus aggregates genuinely independent edges rather
than 13 correlated copies of the same momentum signal.
"""
from __future__ import annotations

from collections import deque
from typing import Deque, List, Optional

from app.consensus.base import Voter
from app.strategies import Bar


# ── helpers ─────────────────────────────────────────────────────────────────


def _ema_alpha(period: int) -> float:
    return 2.0 / (period + 1.0)


# ── moving-average crossover (trend) ────────────────────────────────────────


class MACrossVoter(Voter):
    """Simple-moving-average crossover. +1 when fast SMA > slow SMA, else -1.

    Abstains (0) until ``slow + 1`` bars have been seen, i.e. until both SMAs are
    fully warmed up. Rolling sums + bounded deques keep this O(1) per bar.
    """

    def __init__(self, fast: int, slow: int, weight: float = 1.0):
        if fast >= slow:
            raise ValueError("fast must be < slow")
        self.fast = int(fast)
        self.slow = int(slow)
        self.name = f"ma_{self.fast}_{self.slow}"
        self.weight = float(weight)
        self.reset()

    def reset(self) -> None:
        self._fast_win: Deque[float] = deque(maxlen=self.fast)
        self._slow_win: Deque[float] = deque(maxlen=self.slow)
        self._fast_sum = 0.0
        self._slow_sum = 0.0
        self._n = 0

    def observe(self, bar: Bar) -> int:
        c = float(bar.close)

        if len(self._fast_win) == self.fast:
            self._fast_sum -= self._fast_win[0]
        self._fast_win.append(c)
        self._fast_sum += c

        if len(self._slow_win) == self.slow:
            self._slow_sum -= self._slow_win[0]
        self._slow_win.append(c)
        self._slow_sum += c

        self._n += 1
        if self._n <= self.slow:
            return 0

        fast_sma = self._fast_sum / self.fast
        slow_sma = self._slow_sum / self.slow
        return 1 if fast_sma > slow_sma else -1


# ── RSI mean-reversion ──────────────────────────────────────────────────────


class RSIReversionVoter(Voter):
    """Wilder's RSI as a mean-reversion signal.

    +1 when RSI < 30 (oversold -> expect bounce up), -1 when RSI > 70
    (overbought -> expect pullback), else 0. Abstains until RSI is warm.
    """

    def __init__(self, period: int = 14, weight: float = 1.0):
        self.period = int(period)
        self.name = f"rsi_rev_{self.period}"
        self.weight = float(weight)
        self.reset()

    def reset(self) -> None:
        self._prev_close: Optional[float] = None
        self._avg_gain = 0.0
        self._avg_loss = 0.0
        self._count = 0  # number of deltas seen
        self._seed_gain = 0.0
        self._seed_loss = 0.0

    def observe(self, bar: Bar) -> int:
        c = float(bar.close)
        if self._prev_close is None:
            self._prev_close = c
            return 0

        delta = c - self._prev_close
        self._prev_close = c
        gain = delta if delta > 0 else 0.0
        loss = -delta if delta < 0 else 0.0
        self._count += 1

        if self._count <= self.period:
            # Accumulate the seed (simple average over first `period` deltas).
            self._seed_gain += gain
            self._seed_loss += loss
            if self._count < self.period:
                return 0
            self._avg_gain = self._seed_gain / self.period
            self._avg_loss = self._seed_loss / self.period
        else:
            # Wilder smoothing.
            self._avg_gain = (self._avg_gain * (self.period - 1) + gain) / self.period
            self._avg_loss = (self._avg_loss * (self.period - 1) + loss) / self.period

        if self._avg_loss == 0.0:
            rsi = 100.0
        else:
            rs = self._avg_gain / self._avg_loss
            rsi = 100.0 - (100.0 / (1.0 + rs))

        if rsi < 30.0:
            return 1
        if rsi > 70.0:
            return -1
        return 0


# ── MACD (trend/momentum) ───────────────────────────────────────────────────


class MACDVoter(Voter):
    """MACD line vs its signal line. +1 above, -1 below, 0 until warm.

    MACD = EMA(fast) - EMA(slow); signal = EMA(MACD, signal_period). Pure EMA
    recursion -> O(1) state, no windows.
    """

    def __init__(self, fast: int = 12, slow: int = 26, signal: int = 9,
                 weight: float = 1.0):
        if fast >= slow:
            raise ValueError("fast must be < slow")
        self.fast = int(fast)
        self.slow = int(slow)
        self.signal = int(signal)
        self.name = "macd"
        self.weight = float(weight)
        self._a_fast = _ema_alpha(self.fast)
        self._a_slow = _ema_alpha(self.slow)
        self._a_sig = _ema_alpha(self.signal)
        self.reset()

    def reset(self) -> None:
        self._ema_fast: Optional[float] = None
        self._ema_slow: Optional[float] = None
        self._sig: Optional[float] = None
        self._n = 0
        self._macd_count = 0

    def observe(self, bar: Bar) -> int:
        c = float(bar.close)
        self._n += 1

        if self._ema_fast is None:
            self._ema_fast = c
            self._ema_slow = c
        else:
            self._ema_fast += self._a_fast * (c - self._ema_fast)
            self._ema_slow += self._a_slow * (c - self._ema_slow)

        # Let the slow EMA warm up before trusting the MACD line.
        if self._n < self.slow:
            return 0

        macd = self._ema_fast - self._ema_slow
        if self._sig is None:
            self._sig = macd
            self._macd_count = 1
            return 0
        self._sig += self._a_sig * (macd - self._sig)
        self._macd_count += 1
        if self._macd_count < self.signal:
            return 0

        return 1 if macd > self._sig else -1


# ── Bollinger bands (mean-reversion + breakout) ─────────────────────────────


class _RollingStats:
    """Bounded rolling mean/std (population) over the last `window` closes."""

    def __init__(self, window: int):
        self.window = int(window)
        self._win: Deque[float] = deque(maxlen=self.window)
        self._sum = 0.0
        self._sumsq = 0.0

    def push(self, x: float) -> None:
        if len(self._win) == self.window:
            old = self._win[0]
            self._sum -= old
            self._sumsq -= old * old
        self._win.append(x)
        self._sum += x
        self._sumsq += x * x

    @property
    def full(self) -> bool:
        return len(self._win) == self.window

    @property
    def mean(self) -> float:
        return self._sum / len(self._win)

    @property
    def std(self) -> float:
        n = len(self._win)
        var = self._sumsq / n - (self._sum / n) ** 2
        return var ** 0.5 if var > 0 else 0.0


class _BollingerBase(Voter):
    def __init__(self, period: int = 20, num_std: float = 2.0, weight: float = 1.0):
        self.period = int(period)
        self.num_std = float(num_std)
        self.weight = float(weight)
        self.reset()

    def reset(self) -> None:
        self._stats = _RollingStats(self.period)

    def _bands(self, close: float) -> Optional[tuple[float, float]]:
        self._stats.push(close)
        if not self._stats.full:
            return None
        mean = self._stats.mean
        sd = self._stats.std
        return mean - self.num_std * sd, mean + self.num_std * sd


class BollingerReversionVoter(_BollingerBase):
    """Fade band touches. +1 when close < lower band, -1 when close > upper."""

    def __init__(self, period: int = 20, num_std: float = 2.0, weight: float = 1.0):
        super().__init__(period, num_std, weight)
        self.name = "boll_rev"

    def observe(self, bar: Bar) -> int:
        c = float(bar.close)
        bands = self._bands(c)
        if bands is None:
            return 0
        lower, upper = bands
        if c < lower:
            return 1
        if c > upper:
            return -1
        return 0


class BollingerBreakoutVoter(_BollingerBase):
    """Ride band breaks. +1 when close > upper band, -1 when close < lower."""

    def __init__(self, period: int = 20, num_std: float = 2.0, weight: float = 1.0):
        super().__init__(period, num_std, weight)
        self.name = "boll_brk"

    def observe(self, bar: Bar) -> int:
        c = float(bar.close)
        bands = self._bands(c)
        if bands is None:
            return 0
        lower, upper = bands
        if c > upper:
            return 1
        if c < lower:
            return -1
        return 0


# ── Donchian channel breakout ───────────────────────────────────────────────


class DonchianBreakoutVoter(Voter):
    """Donchian-channel breakout. +1 on a new N-bar high, -1 on a new N-bar low.

    The channel is computed over the *prior* N bars (the current bar is compared
    against the trailing window), so a close at or above the rolling max high is
    a fresh breakout. Abstains until the window has N bars.
    """

    def __init__(self, period: int = 20, weight: float = 1.0):
        self.period = int(period)
        self.name = f"donchian_{self.period}"
        self.weight = float(weight)
        self.reset()

    def reset(self) -> None:
        self._highs: Deque[float] = deque(maxlen=self.period)
        self._lows: Deque[float] = deque(maxlen=self.period)

    def observe(self, bar: Bar) -> int:
        h = float(bar.high)
        l = float(bar.low)
        c = float(bar.close)

        if len(self._highs) < self.period:
            self._highs.append(h)
            self._lows.append(l)
            return 0

        max_high = max(self._highs)
        min_low = min(self._lows)

        self._highs.append(h)
        self._lows.append(l)

        if c >= max_high:
            return 1
        if c <= min_low:
            return -1
        return 0


# ── ATR regime filter ───────────────────────────────────────────────────────


class ATRRegimeVoter(Voter):
    """Volatility-gated trend filter.

    Abstains (0) in low-volatility chop (ATR/price < ``min_atr_pct``). When
    volatility is sufficient, votes with the longer-horizon trend: +1 if the
    close is above the close ``trend_lookback`` bars ago, -1 if below.
    """

    def __init__(self, period: int = 14, min_atr_pct: float = 0.003,
                 trend_lookback: int = 20, weight: float = 1.0):
        self.period = int(period)
        self.min_atr_pct = float(min_atr_pct)
        self.trend_lookback = int(trend_lookback)
        self.name = "atr_regime"
        self.weight = float(weight)
        self.reset()

    def reset(self) -> None:
        self._prev_close: Optional[float] = None
        self._atr: Optional[float] = None
        self._tr_count = 0
        self._tr_seed = 0.0
        # Keep the last (trend_lookback + 1) closes to compare horizons.
        self._closes: Deque[float] = deque(maxlen=self.trend_lookback + 1)

    def _true_range(self, bar: Bar) -> float:
        h = float(bar.high)
        l = float(bar.low)
        if self._prev_close is None:
            return h - l
        pc = self._prev_close
        return max(h - l, abs(h - pc), abs(l - pc))

    def observe(self, bar: Bar) -> int:
        c = float(bar.close)
        tr = self._true_range(bar)

        # Wilder-smoothed ATR.
        self._tr_count += 1
        if self._atr is None:
            if self._tr_count <= self.period:
                self._tr_seed += tr
                if self._tr_count == self.period:
                    self._atr = self._tr_seed / self.period
        else:
            self._atr = (self._atr * (self.period - 1) + tr) / self.period

        self._prev_close = c
        self._closes.append(c)

        # Not warm yet (need ATR and a full trend window).
        if self._atr is None or len(self._closes) <= self.trend_lookback:
            return 0

        if c <= 0 or (self._atr / c) < self.min_atr_pct:
            return 0  # low-vol chop -> abstain

        ref = self._closes[0]  # close `trend_lookback` bars ago
        if c > ref:
            return 1
        if c < ref:
            return -1
        return 0


# ── default ensemble ─────────────────────────────────────────────────────────


def build_default_voters() -> List[Voter]:
    """Return one instance of every voter (13 total) with unique names.

    4 MA crossovers + 3 RSI + 1 MACD + 2 Bollinger + 2 Donchian + 1 ATR regime.
    """
    voters: List[Voter] = [
        MACrossVoter(5, 20),
        MACrossVoter(10, 30),
        MACrossVoter(20, 50),
        MACrossVoter(50, 100),
        RSIReversionVoter(7),
        RSIReversionVoter(14),
        RSIReversionVoter(21),
        MACDVoter(12, 26, 9),
        BollingerReversionVoter(20, 2.0),
        BollingerBreakoutVoter(20, 2.0),
        DonchianBreakoutVoter(20),
        DonchianBreakoutVoter(55),
        ATRRegimeVoter(14, 0.003, 20),
    ]
    return voters


__all__ = [
    "MACrossVoter",
    "RSIReversionVoter",
    "MACDVoter",
    "BollingerReversionVoter",
    "BollingerBreakoutVoter",
    "DonchianBreakoutVoter",
    "ATRRegimeVoter",
    "build_default_voters",
]
