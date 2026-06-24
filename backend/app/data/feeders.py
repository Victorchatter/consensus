from __future__ import annotations

import datetime as dt
from abc import ABC, abstractmethod
from typing import List, Optional

import httpx

from app.core.config import settings

UTC = dt.timezone.utc

# Lazy import yfinance — heavy dependency that may fail on some installs
_yf = None


def _get_yf():
    global _yf
    if _yf is None:
        try:
            import yfinance as yf
            _yf = yf
        except Exception as e:
            print(f"[WARN] yfinance not available: {e}")
            _yf = False
    return _yf


class OHLCVBar:
    def __init__(
        self,
        timestamp: dt.datetime,
        open_: float,
        high: float,
        low: float,
        close: float,
        volume: Optional[float] = None,
    ):
        self.timestamp = timestamp
        self.open = open_
        self.high = high
        self.low = low
        self.close = close
        self.volume = volume


class DataFeeder(ABC):
    @abstractmethod
    def fetch_historical(
        self, symbol: str, start: dt.date, end: dt.date, timeframe: str = "1d"
    ) -> List[OHLCVBar]:
        ...


class YahooFinanceFeeder(DataFeeder):
    """Free historical data via yfinance."""

    # yfinance interval mapping + max lookback in days
    TF_MAP: dict[str, tuple[str, int]] = {
        "1m": ("1m", 7),
        "5m": ("5m", 60),
        "15m": ("15m", 60),
        "1h": ("1h", 730),
        "4h": ("1h", 730),  # yfinance has no native 4h; fetch 1h
        "1d": ("1d", 365 * 10),
        "1w": ("1wk", 365 * 10),
        "1wk": ("1wk", 365 * 10),
    }

    def fetch_historical(
        self, symbol: str, start: dt.date, end: dt.date, timeframe: str = "1d"
    ) -> List[OHLCVBar]:
        yf = _get_yf()
        if not yf:
            return []
        yf_tf, max_days = self.TF_MAP.get(timeframe, ("1d", 365 * 10))

        # Clamp start date to yfinance's lookback limit for intraday intervals
        max_start = end - dt.timedelta(days=max_days)
        effective_start = max(start, max_start)

        try:
            ticker = yf.Ticker(symbol)
            df = ticker.history(start=effective_start, end=end, interval=yf_tf, auto_adjust=True)
            if df.empty:
                print(f"[YahooFinance] No data returned for {symbol} ({timeframe}) {effective_start} ->{end}")
                return []
            bars: List[OHLCVBar] = []
            for ts, row in df.iterrows():
                # ts is a pandas Timestamp; .to_pydatetime() works without explicit pandas import
                ts_py = ts.to_pydatetime() if hasattr(ts, "to_pydatetime") else dt.datetime.fromisoformat(str(ts))
                vol = row["Volume"]
                # NaN-safe check: NaN != NaN, None is not None ->safe
                volume = float(vol) if vol is not None and vol == vol else None
                bars.append(
                    OHLCVBar(
                        timestamp=ts_py,
                        open_=float(row["Open"]),
                        high=float(row["High"]),
                        low=float(row["Low"]),
                        close=float(row["Close"]),
                        volume=volume,
                    )
                )
            # If user requested 4h, downsample 1h bars by taking every 4th bar
            if timeframe == "4h" and len(bars) >= 4:
                bars = bars[::4]
            print(f"[YahooFinance] Fetched {len(bars)} bars for {symbol} ({timeframe}) {effective_start} ->{end}")
            return bars
        except Exception as e:
            print(f"[YahooFinance] Error fetching {symbol}: {e}")
            return []


class AlpacaFeeder(DataFeeder):
    """Stocks/ETFs via Alpaca Markets."""

    def __init__(self):
        self.api_key = settings.alpaca_api_key
        self.secret_key = settings.alpaca_secret_key
        self.paper = settings.alpaca_paper
        self.base_url = (
            "https://paper-api.alpaca.markets" if self.paper else "https://api.alpaca.markets"
        )

    def fetch_historical(
        self, symbol: str, start: dt.date, end: dt.date, timeframe: str = "1d"
    ) -> List[OHLCVBar]:
        if not self.api_key:
            return []
        tf_map = {
            "1m": "1Min",
            "5m": "5Min",
            "15m": "15Min",
            "1h": "1Hour",
            "1d": "1Day",
            "1w": "1Week",
        }
        alpaca_tf = tf_map.get(timeframe, "1Day")
        url = f"{self.base_url}/v2/stocks/{symbol}/bars"
        headers = {
            "APCA-API-KEY-ID": self.api_key,
            "APCA-API-SECRET-KEY": self.secret_key,
        }
        params = {
            "start": start.isoformat(),
            "end": end.isoformat(),
            "timeframe": alpaca_tf,
            "adjustment": "all",
            "feed": "sip" if not self.paper else "iex",
        }
        try:
            r = httpx.get(url, headers=headers, params=params, timeout=30.0)
            r.raise_for_status()
            data = r.json()
            bars: List[OHLCVBar] = []
            for b in data.get("bars", []):
                bars.append(
                    OHLCVBar(
                        timestamp=dt.datetime.fromisoformat(b["t"].replace("Z", "+00:00")),
                        open_=float(b["o"]),
                        high=float(b["h"]),
                        low=float(b["l"]),
                        close=float(b["c"]),
                        volume=float(b["v"]),
                    )
                )
            return bars
        except Exception:
            return []


def parse_ohlcv(rows: List[list]) -> List[OHLCVBar]:
    """Convert ccxt OHLCV rows into OHLCVBars.

    ccxt returns rows shaped ``[ms_timestamp, open, high, low, close, volume]``
    where the timestamp is epoch milliseconds (UTC). This is a pure helper so it
    can be tested without touching the network.
    """
    bars: List[OHLCVBar] = []
    for row in rows:
        ms, o, h, l, c = row[0], row[1], row[2], row[3], row[4]
        v = row[5] if len(row) > 5 else None
        bars.append(
            OHLCVBar(
                timestamp=dt.datetime.fromtimestamp(ms / 1000, tz=UTC),
                open_=float(o),
                high=float(h),
                low=float(l),
                close=float(c),
                volume=None if v is None else float(v),
            )
        )
    return bars


class CCXTFeeder(DataFeeder):
    """Crypto OHLCV via ccxt (Binance/Kraken/Coinbase/etc.)."""

    # ccxt uses the same canonical interval strings we do, except it has no
    # native weekly on every exchange — map to what ccxt expects.
    TF_MAP: dict[str, str] = {
        "1m": "1m",
        "5m": "5m",
        "15m": "15m",
        "30m": "30m",
        "1h": "1h",
        "4h": "4h",
        "1d": "1d",
        "1w": "1w",
    }

    def __init__(self, exchange_id: str = "binance"):
        self.exchange_id = exchange_id

    def fetch_historical(
        self, symbol: str, start: dt.date, end: dt.date, timeframe: str = "1d"
    ) -> List[OHLCVBar]:
        # Lazy import — ccxt is an optional dependency and the network is the
        # only thing it is good for, so keep it out of import time.
        try:
            import ccxt  # type: ignore
        except Exception as e:  # pragma: no cover - import guard
            print(f"[WARN] ccxt not available: {e}")
            return []

        ccxt_tf = self.TF_MAP.get(timeframe, "1d")

        def _to_ms(value: dt.date) -> int:
            if isinstance(value, dt.datetime):
                d = value if value.tzinfo else value.replace(tzinfo=UTC)
            else:
                d = dt.datetime(value.year, value.month, value.day, tzinfo=UTC)
            return int(d.timestamp() * 1000)

        start_ms = _to_ms(start)
        end_ms = _to_ms(end)

        try:
            exchange_cls = getattr(ccxt, self.exchange_id)
            exchange = exchange_cls({"enableRateLimit": True})
            limit = 1000
            since = start_ms
            all_rows: List[list] = []
            while since < end_ms:
                batch = exchange.fetch_ohlcv(symbol, timeframe=ccxt_tf, since=since, limit=limit)
                if not batch:
                    break
                all_rows.extend(batch)
                last_ms = batch[-1][0]
                # Advance past the last bar; stop if the exchange didn't progress.
                next_since = last_ms + 1
                if next_since <= since:
                    break
                since = next_since
                if len(batch) < limit:
                    break
            # Drop anything beyond the requested end window.
            all_rows = [r for r in all_rows if r[0] <= end_ms]
            bars = parse_ohlcv(all_rows)
            print(
                f"[CCXT:{self.exchange_id}] Fetched {len(bars)} bars for {symbol} "
                f"({timeframe}) {start} ->{end}"
            )
            return bars
        except Exception as e:
            print(f"[CCXT:{self.exchange_id}] Error fetching {symbol}: {e}")
            return []


# Sources that map onto a ccxt exchange. "ccxt" is a generic alias -> binance.
_CCXT_SOURCES: dict[str, str] = {
    "binance": "binance",
    "kraken": "kraken",
    "coinbase": "coinbase",
    "ccxt": "binance",
}


def get_feeder_for_source(source: str) -> DataFeeder:
    if source == "alpaca":
        return AlpacaFeeder()
    if source in _CCXT_SOURCES:
        return CCXTFeeder(_CCXT_SOURCES[source])
    return YahooFinanceFeeder()
