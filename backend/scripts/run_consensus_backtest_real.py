"""Real-data consensus backtest: load ingested bars from SQLite, run the same
walk-forward threshold sweep as Phase-1, and render a Markdown report.

Reads ONLY through the canonical loader (`load_bars`) — no network, no synthetic
data. Ingest first (see HANDOFF §6), e.g.:
    python -m app.consensus.ingest --symbol BTC/USDT --source binance --timeframe 5m --start 2022-01-01 --end 2026-06-24
    python -m app.consensus.ingest --symbol SPY --source yahoo --timeframe 5m --start 2026-04-28 --end 2026-06-24
    python -m app.consensus.ingest --symbol GLD --source yahoo --timeframe 5m --start 2026-04-28 --end 2026-06-24

Run:
    ./venv/Scripts/python.exe scripts/run_consensus_backtest_real.py
"""
from __future__ import annotations

import datetime as dt
import os
import sys

_BACKEND_DIR = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
if _BACKEND_DIR not in sys.path:
    sys.path.insert(0, _BACKEND_DIR)

from app import models  # noqa: E402
from app.core.database import SessionLocal  # noqa: E402
from app.consensus import report, sweep  # noqa: E402
from app.data.loader import load_bars  # noqa: E402

_OUT_PATH = os.path.normpath(
    os.path.join(_BACKEND_DIR, "..", "docs", "consensus-real-backtest-report.md")
)

# (symbol, asset_class, timeframe, start, end). BTC has deep 5m history via ccxt;
# Yahoo only serves ~the last 60 days of 5m for SPY/GLD.
_UNIVERSE = [
    ("BTC/USDT", "crypto", "5m", dt.date(2022, 1, 1), dt.date(2026, 6, 24)),
    ("SPY", "etf", "5m", dt.date(2026, 4, 28), dt.date(2026, 6, 24)),
    ("GLD", "commodity", "5m", dt.date(2026, 4, 28), dt.date(2026, 6, 24)),
]


def build_datasets(db) -> list[dict]:
    datasets: list[dict] = []
    for symbol, asset_class, tf, start, end in _UNIVERSE:
        asset = db.query(models.Asset).filter(models.Asset.symbol == symbol).first()
        if asset is None:
            print(f"  [skip] {symbol}: no Asset row — ingest it first")
            continue
        bars, quality = load_bars(db, asset.id, tf, start, end, asset_class)
        if not bars:
            print(f"  [skip] {symbol}: 0 bars in range — ingest it first")
            continue
        flag = "clean" if quality.is_clean else f"DIRTY {quality.warnings}"
        print(
            f"  {symbol:<9} {asset_class:<10} {tf}  {len(bars):>7} bars  "
            f"{bars[0].timestamp:%Y-%m-%d} -> {bars[-1].timestamp:%Y-%m-%d}  "
            f"dupes={quality.n_duplicates_removed} gaps={quality.n_gaps} [{flag}]"
        )
        datasets.append(
            {"bars": bars, "asset_class": asset_class, "timeframe": tf, "symbol": symbol}
        )
    return datasets


def main() -> int:
    db = SessionLocal()
    try:
        print("Loading real ingested datasets from SQLite...")
        datasets = build_datasets(db)
    finally:
        db.close()

    if not datasets:
        print("No datasets loaded. Run the ingest commands first (see module docstring).")
        return 1

    print(f"\nRunning consensus sweep over {len(datasets)} real datasets...")
    results = sweep.run_multi(datasets)
    text = report.write_report(results, _OUT_PATH)

    for r in results:
        per = r.get("per_threshold", {}) or {}
        best = r.get("best_threshold")
        row = per.get(str(best), {}) if best is not None else {}
        print(
            f"  {r.get('symbol'):<9} {r.get('asset_class'):<10} {r.get('timeframe'):<3}  "
            f"best_thr={best}  sharpe={row.get('sharpe', 0.0)}  "
            f"return={row.get('total_return_pct', 0.0)}%  trades={row.get('n_trades', 0)}  "
            f"(folds={r.get('n_folds')})"
        )

    print(f"\nReport written: {_OUT_PATH}  ({len(text)} chars)")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
