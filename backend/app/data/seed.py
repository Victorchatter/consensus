from __future__ import annotations

from sqlalchemy.orm import Session

from app.core.database import SessionLocal
from app import models

DEFAULT_ASSETS = [
    # US Stocks
    {"symbol": "AAPL", "name": "Apple Inc.", "asset_class": models.AssetClass.STOCK, "exchange": "NASDAQ", "data_source": "yahoo"},
    {"symbol": "MSFT", "name": "Microsoft Corp.", "asset_class": models.AssetClass.STOCK, "exchange": "NASDAQ", "data_source": "yahoo"},
    {"symbol": "GOOGL", "name": "Alphabet Inc.", "asset_class": models.AssetClass.STOCK, "exchange": "NASDAQ", "data_source": "yahoo"},
    {"symbol": "AMZN", "name": "Amazon.com Inc.", "asset_class": models.AssetClass.STOCK, "exchange": "NASDAQ", "data_source": "yahoo"},
    {"symbol": "NVDA", "name": "NVIDIA Corp.", "asset_class": models.AssetClass.STOCK, "exchange": "NASDAQ", "data_source": "yahoo"},
    {"symbol": "TSLA", "name": "Tesla Inc.", "asset_class": models.AssetClass.STOCK, "exchange": "NASDAQ", "data_source": "yahoo"},
    {"symbol": "META", "name": "Meta Platforms Inc.", "asset_class": models.AssetClass.STOCK, "exchange": "NASDAQ", "data_source": "yahoo"},
    {"symbol": "SPY", "name": "SPDR S&P 500 ETF", "asset_class": models.AssetClass.ETF, "exchange": "NYSE", "data_source": "yahoo"},
    {"symbol": "QQQ", "name": "Invesco QQQ ETF", "asset_class": models.AssetClass.ETF, "exchange": "NASDAQ", "data_source": "yahoo"},
    # Crypto
    {"symbol": "BTC-USD", "name": "Bitcoin USD", "asset_class": models.AssetClass.CRYPTO, "exchange": "CCXT", "data_source": "yahoo"},
    {"symbol": "ETH-USD", "name": "Ethereum USD", "asset_class": models.AssetClass.CRYPTO, "exchange": "CCXT", "data_source": "yahoo"},
    # Forex (via Yahoo)
    {"symbol": "EURUSD=X", "name": "EUR/USD", "asset_class": models.AssetClass.FOREX, "exchange": "OANDA", "data_source": "yahoo"},
    {"symbol": "GBPUSD=X", "name": "GBP/USD", "asset_class": models.AssetClass.FOREX, "exchange": "OANDA", "data_source": "yahoo"},
    # Commodities
    {"symbol": "GC=F", "name": "Gold Futures", "asset_class": models.AssetClass.COMMODITY, "exchange": "COMEX", "data_source": "yahoo"},
    {"symbol": "CL=F", "name": "Crude Oil Futures", "asset_class": models.AssetClass.COMMODITY, "exchange": "NYMEX", "data_source": "yahoo"},
]


def seed_assets(db: Session) -> None:
    existing = {a.symbol for a in db.query(models.Asset.symbol).all()}
    for item in DEFAULT_ASSETS:
        if item["symbol"] in existing:
            continue
        asset = models.Asset(**item)
        db.add(asset)
    db.commit()


def seed_strategies(db: Session) -> None:
    builtins = [
        {
            "name": "SMA Crossover",
            "class_path": "app.strategies.builtin.sma_cross.SMACrossStrategy",
            "params_schema": {
                "fast_period": {"type": "integer", "default": 10, "min": 2, "max": 100},
                "slow_period": {"type": "integer", "default": 30, "min": 5, "max": 200},
            },
            "description": "Classic trend-following strategy. Buys when fast SMA crosses above slow SMA, sells on reverse cross.",
            "is_builtin": True,
        },
        {
            "name": "RSI Mean Reversion",
            "class_path": "app.strategies.builtin.rsi_reversion.RSIMeanReversionStrategy",
            "params_schema": {
                "period": {"type": "integer", "default": 14, "min": 5, "max": 50},
                "oversold": {"type": "integer", "default": 30, "min": 10, "max": 40},
                "overbought": {"type": "integer", "default": 70, "min": 60, "max": 90},
            },
            "description": "Mean reversion using RSI. Buys when RSI drops below oversold, sells when RSI rises above overbought.",
            "is_builtin": True,
        },
        {
            "name": "Bollinger Bands Breakout",
            "class_path": "app.strategies.builtin.bollinger.BollingerBreakoutStrategy",
            "params_schema": {
                "period": {"type": "integer", "default": 20, "min": 10, "max": 100},
                "std_dev": {"type": "float", "default": 2.0, "min": 0.5, "max": 5.0},
            },
            "description": "Breakout strategy using Bollinger Bands. Buys on close above upper band, sells on close below lower band.",
            "is_builtin": True,
        },
        {
            "name": "MACD Momentum",
            "class_path": "app.strategies.builtin.macd.MACDMomentumStrategy",
            "params_schema": {
                "fast": {"type": "integer", "default": 12, "min": 5, "max": 50},
                "slow": {"type": "integer", "default": 26, "min": 10, "max": 100},
                "signal": {"type": "integer", "default": 9, "min": 5, "max": 50},
            },
            "description": "Momentum strategy using MACD histogram crossover. Buys on bullish MACD crossover, sells on bearish.",
            "is_builtin": True,
        },
    ]
    existing = {s.name for s in db.query(models.Strategy.name).all()}
    for item in builtins:
        if item["name"] in existing:
            continue
        strategy = models.Strategy(**item)
        db.add(strategy)
    db.commit()


def run_seed() -> None:
    db = SessionLocal()
    try:
        seed_assets(db)
        seed_strategies(db)
    finally:
        db.close()
