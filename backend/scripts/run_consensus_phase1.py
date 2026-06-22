"""
Phase-1 driver: generate synthetic multi-asset datasets, run the full
walk-forward consensus-threshold sweep, and render the Markdown report.

No network is touched — all bars come from app/consensus/synth.py. See the
"How to regenerate with REAL data" section of the emitted report for the live
ingest path.

Run:
    ./venv/Scripts/python.exe scripts/run_consensus_phase1.py
"""
from __future__ import annotations

import os
import sys

# Make `app` importable when run as a script from anywhere.
_BACKEND_DIR = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
if _BACKEND_DIR not in sys.path:
    sys.path.insert(0, _BACKEND_DIR)

from app.consensus import report, sweep  # noqa: E402
from app.consensus.synth import synthetic_bars  # noqa: E402


# Output path: backend/../docs/consensus-phase1-report.md
_OUT_PATH = os.path.normpath(
    os.path.join(_BACKEND_DIR, "..", "docs", "consensus-phase1-report.md")
)


def build_datasets() -> list[dict]:
    """Synthetic multi-asset datasets covering crypto/etf/commodity, 1m + 5m."""
    return [
        {
            "bars": synthetic_bars(
                2500, "5m", seed=1, start_price=30000.0, regime="trend", vol=0.004
            ),
            "asset_class": "crypto",
            "timeframe": "5m",
            "symbol": "BTC-USD",
        },
        {
            "bars": synthetic_bars(
                4000, "1m", seed=2, start_price=30000.0, regime="trend", vol=0.004
            ),
            "asset_class": "crypto",
            "timeframe": "1m",
            "symbol": "BTC-USD",
        },
        {
            "bars": synthetic_bars(
                2500, "5m", seed=3, start_price=500.0, regime="trend", vol=0.0015
            ),
            "asset_class": "etf",
            "timeframe": "5m",
            "symbol": "SPY",
        },
        {
            "bars": synthetic_bars(
                2500, "5m", seed=4, start_price=180.0, regime="chop", vol=0.0025
            ),
            "asset_class": "commodity",
            "timeframe": "5m",
            "symbol": "GLD",
        },
    ]


def main() -> int:
    datasets = build_datasets()
    print(f"Running consensus Phase-1 sweep over {len(datasets)} synthetic datasets...")

    results = sweep.run_multi(datasets)

    text = report.write_report(results, _OUT_PATH)

    # One-line summary per dataset.
    for r in results:
        per = r.get("per_threshold", {}) or {}
        best = r.get("best_threshold")
        row = per.get(str(best), {}) if best is not None else {}
        sharpe = row.get("sharpe", 0.0)
        ret = row.get("total_return_pct", 0.0)
        nt = row.get("n_trades", 0)
        print(
            f"  {r.get('symbol'):<8} {r.get('asset_class'):<10} "
            f"{r.get('timeframe'):<3}  best_thr={best}  "
            f"sharpe={sharpe}  return={ret}%  trades={nt}  "
            f"(folds={r.get('n_folds')})"
        )

    print(f"\nReport written: {_OUT_PATH}  ({len(text)} chars)")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
