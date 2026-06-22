"""Tests for the Phase-1 consensus Markdown report renderer."""
from __future__ import annotations

import os

from app.consensus.report import write_report


def _sample_results() -> list[dict]:
    return [
        {
            "timeframe": "5m",
            "asset_class": "crypto",
            "symbol": "BTC-USD",
            "n_bars": 2500,
            "n_folds": 14,
            "per_threshold": {
                "0.5": {
                    "threshold": 0.5,
                    "total_return_pct": 3.21,
                    "sharpe": 0.42,
                    "sortino": 0.61,
                    "max_drawdown_pct": 5.5,
                    "win_rate": 0.55,
                    "n_trades": 40,
                    "avg_trade_bars": 6.0,
                },
                "0.7": {
                    "threshold": 0.7,
                    "total_return_pct": -1.10,
                    "sharpe": -0.20,
                    "sortino": -0.30,
                    "max_drawdown_pct": 7.2,
                    "win_rate": 0.45,
                    "n_trades": 18,
                    "avg_trade_bars": 9.0,
                },
            },
            "best_threshold": 0.5,
            "data_quality": {
                "n_bars": 2500,
                "n_folds": 14,
                "train_size": 300,
                "test_size": 150,
                "commission_pct": 0.001,
                "slippage_pct": 0.0005,
            },
        },
        {
            "timeframe": "5m",
            "asset_class": "etf",
            "symbol": "SPY",
            "n_bars": 2500,
            "n_folds": 14,
            "per_threshold": {
                "0.5": {
                    "threshold": 0.5,
                    "total_return_pct": -2.0,
                    "sharpe": -0.5,
                    "sortino": -0.7,
                    "max_drawdown_pct": 6.0,
                    "win_rate": 0.40,
                    "n_trades": 30,
                    "avg_trade_bars": 5.0,
                },
            },
            "best_threshold": 0.5,
            "data_quality": {
                "n_bars": 2500,
                "n_folds": 14,
                "train_size": 300,
                "test_size": 150,
                "commission_pct": 0.0005,
                "slippage_pct": 0.0005,
            },
        },
    ]


def test_write_report_writes_file_with_key_strings(tmp_path):
    out = tmp_path / "phase1.md"
    text = write_report(_sample_results(), str(out))

    assert os.path.exists(str(out))
    on_disk = out.read_text(encoding="utf-8")

    # returned string matches file
    assert text == on_disk

    # table header present
    assert "Threshold" in on_disk
    # symbols present
    assert "BTC-USD" in on_disk
    assert "SPY" in on_disk
    # a verdict paragraph
    assert "Verdict" in on_disk
    # honest "no edge" surfaced for the negative-sharpe SPY section
    assert "NO EDGE" in on_disk
    # regeneration section present
    assert "How to regenerate with REAL data" in on_disk


def test_write_report_marks_best_threshold(tmp_path):
    out = tmp_path / "phase1b.md"
    write_report(_sample_results(), str(out))
    on_disk = out.read_text(encoding="utf-8")
    assert "Best threshold:" in on_disk
    assert "(best)" in on_disk
