"""Tests for the walk-forward consensus-threshold sweep (Section 6)."""
from __future__ import annotations

from app.consensus.sweep import run_threshold_sweep
from app.consensus.synth import synthetic_bars


def test_run_threshold_sweep_basic():
    bars = synthetic_bars(900, "5m", seed=5, regime="trend")
    result = run_threshold_sweep(
        bars,
        train_size=250,
        test_size=120,
        thresholds=(0.5, 0.7, 0.9),
    )

    assert isinstance(result, dict)
    assert result["n_bars"] == 900

    per = result["per_threshold"]
    for t in (0.5, 0.7, 0.9):
        assert str(t) in per, f"missing threshold {t}"
        pt = per[str(t)]
        assert pt["threshold"] == t
        assert "total_return_pct" in pt
        assert "sharpe" in pt
        assert "n_trades" in pt

    assert result["best_threshold"] in (0.5, 0.7, 0.9)

    # Stricter consensus should trade no more than looser consensus.
    assert per["0.9"]["n_trades"] <= per["0.5"]["n_trades"]


def test_run_threshold_sweep_has_folds():
    bars = synthetic_bars(900, "5m", seed=5, regime="trend")
    result = run_threshold_sweep(
        bars,
        train_size=250,
        test_size=120,
        thresholds=(0.5, 0.7, 0.9),
    )
    assert result["n_folds"] >= 1
    assert result["asset_class"] == "crypto"
    assert result["data_quality"]["commission_pct"] == 0.001
