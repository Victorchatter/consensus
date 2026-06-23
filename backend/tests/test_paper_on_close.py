from app.execution.paper import PaperTradingEngine


def test_on_close_fires_for_long_roundtrip():
    closed = []
    # Use 1M balance so position cap doesn't interfere
    eng = PaperTradingEngine(initial_balance=1_000_000.0, on_close=closed.append)
    eng.place_order(asset_id=1, symbol="BTC/USDT", action="buy", size=1.0)
    eng.on_price_update(1, "BTC/USDT", 40_000.0)   # fill the open
    eng.place_order(asset_id=1, symbol="BTC/USDT", action="sell", size=1.0)
    eng.on_price_update(1, "BTC/USDT", 41_000.0)   # fill the close
    assert len(closed) == 1
    t = closed[0]
    assert t["direction"] == "long"
    assert t["size"] == 1.0
    assert t["exit_price"] > t["entry_price"]
    assert t["pnl"] is not None


def test_on_close_fires_for_short_roundtrip():
    closed = []
    # Use 1M balance so position cap doesn't interfere
    eng = PaperTradingEngine(initial_balance=1_000_000.0, on_close=closed.append)
    eng.place_order(asset_id=1, symbol="BTC/USDT", action="sell", size=1.0)
    eng.on_price_update(1, "BTC/USDT", 40_000.0)   # fill the open short
    eng.place_order(asset_id=1, symbol="BTC/USDT", action="buy", size=1.0)
    eng.on_price_update(1, "BTC/USDT", 39_000.0)   # fill the close (price goes down)
    assert len(closed) == 1
    t = closed[0]
    assert t["direction"] == "short"
    assert t["size"] == 1.0
    assert t["exit_price"] < t["entry_price"]
    assert t["pnl"] is not None
