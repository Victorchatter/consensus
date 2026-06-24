from scripts.run_consensus_paper import build_paper_bot_config


def test_paper_config_is_btc_paper_247():
    cfg = build_paper_bot_config(strategy_id=1)
    assert cfg.mode == "paper"
    assert cfg.data_source == "binance"
    assert cfg.timeframe == "5m"
    assert cfg.max_hold_minutes == 0
    assert cfg.close_before_market_close is False
