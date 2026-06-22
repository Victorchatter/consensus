# EchoTrader Consensus — Phase 1 Report

_Run date: 2026-06-22 — synthetic-data harness validation (no network on the build machine)._

Walk-forward consensus-threshold sweep with realistic commissions and slippage applied to every fill. **All numbers below are from SYNTHETIC data** and exist to validate the harness, not to justify trades. See _How to regenerate with REAL data_ at the bottom.

## Summary: which timeframe wins per asset

- **BTC-USD** (crypto): **NO EDGE on any timeframe** (1m: Sharpe -0.108, 5m: Sharpe -0.004). Best available is 5m but Sharpe <= 0.
- **SPY** (etf): only 5m was swept (5m: Sharpe 0.156); positive Sharpe but no 1m-vs-5m comparison available.
- **GLD** (commodity): **NO EDGE on any timeframe** (5m: Sharpe -0.059). Best available is 5m but Sharpe <= 0.

## Per-dataset threshold sweeps

### BTC-USD — crypto @ 5m

| Threshold | Return % | Sharpe | Sortino | MaxDD % | Win % | #Trades |
|---:|---:|---:|---:|---:|---:|---:|
| 0.50 | -1.39 | -0.1964 | 0.0150 | 2.23 | 37.5% | 16 |
| 0.60 | -0.22 | -0.1971 | 0.0264 | 1.67 | 30.0% | 10 |
| 0.70 | 1.20 | -0.0579 | 0.1550 | 1.25 | 60.0% | 5 |
| 0.80 | 0.68 | -0.0571 | 0.0364 | 1.26 | 60.0% | 5 |
| 0.90 *(best)* | 1.13 | -0.0043 | 0.0679 | 1.26 | 75.0% | 4 |

**Best threshold:** 0.90

**Data quality:** 2500 bars, 14 walk-forward folds (train 300 / test 150 per fold), commission 0.100%, slippage 0.050%.

**Verdict: NO EDGE.** Best threshold 0.90 for BTC-USD @ 5m yields Sharpe -0.004 (<= 0) over 4 out-of-sample trades, net total return 1.13%. After realistic fees and slippage there is **no tradeable edge** here — do not deploy capital on this configuration.

### BTC-USD — crypto @ 1m

| Threshold | Return % | Sharpe | Sortino | MaxDD % | Win % | #Trades |
|---:|---:|---:|---:|---:|---:|---:|
| 0.50 | 1.80 | -0.1313 | 2.4250 | 2.19 | 57.6% | 33 |
| 0.60 | 1.83 | -0.1804 | 0.0813 | 1.45 | 50.0% | 30 |
| 0.70 | -0.07 | -0.1538 | 0.0183 | 1.20 | 53.8% | 26 |
| 0.80 | -0.33 | -0.1942 | -0.0200 | 1.13 | 50.0% | 20 |
| 0.90 *(best)* | -0.67 | -0.1079 | -0.0275 | 1.13 | 44.5% | 9 |

**Best threshold:** 0.90

**Data quality:** 4000 bars, 24 walk-forward folds (train 300 / test 150 per fold), commission 0.100%, slippage 0.050%.

**Verdict: NO EDGE.** Best threshold 0.90 for BTC-USD @ 1m yields Sharpe -0.108 (<= 0) over 9 out-of-sample trades, net total return -0.67%. After realistic fees and slippage there is **no tradeable edge** here — do not deploy capital on this configuration.

### SPY — etf @ 5m

| Threshold | Return % | Sharpe | Sortino | MaxDD % | Win % | #Trades |
|---:|---:|---:|---:|---:|---:|---:|
| 0.50 *(best)* | 0.36 | 0.1564 | 0.2600 | 0.53 | 35.0% | 20 |
| 0.60 | -0.06 | -0.0243 | 0.1579 | 0.53 | 40.0% | 15 |
| 0.70 | -0.01 | -0.0450 | 0.1936 | 0.41 | 22.2% | 9 |
| 0.80 | 0.44 | 0.0629 | 0.4114 | 0.32 | 33.3% | 6 |
| 0.90 | -0.15 | -0.1214 | 0.0429 | 0.32 | 0.0% | 3 |

**Best threshold:** 0.50

**Data quality:** 2500 bars, 14 walk-forward folds (train 300 / test 150 per fold), commission 0.050%, slippage 0.050%.

**Verdict: MARGINAL EDGE.** Best threshold 0.50 for SPY @ 5m produces a positive out-of-sample Sharpe of 0.156 across 20 trades, net total return 0.36% after fees + slippage. This is a marginal signal on synthetic data only — it must be re-run on REAL ingested bars before any capital is risked.

### GLD — commodity @ 5m

| Threshold | Return % | Sharpe | Sortino | MaxDD % | Win % | #Trades |
|---:|---:|---:|---:|---:|---:|---:|
| 0.50 | -0.12 | -0.0664 | -0.0221 | 0.86 | 70.3% | 37 |
| 0.60 | -0.64 | -0.1571 | -0.1614 | 0.86 | 73.1% | 26 |
| 0.70 | 0.10 | -0.0650 | -0.0257 | 0.55 | 64.3% | 14 |
| 0.80 | 0.10 | -0.0979 | -0.0186 | 0.55 | 66.7% | 12 |
| 0.90 *(best)* | 0.06 | -0.0593 | -0.0257 | 0.32 | 60.0% | 5 |

**Best threshold:** 0.90

**Data quality:** 2500 bars, 14 walk-forward folds (train 300 / test 150 per fold), commission 0.030%, slippage 0.050%.

**Verdict: NO EDGE.** Best threshold 0.90 for GLD @ 5m yields Sharpe -0.059 (<= 0) over 5 out-of-sample trades, net total return 0.06%. After realistic fees and slippage there is **no tradeable edge** here — do not deploy capital on this configuration.

## How to regenerate with REAL data

Everything above is generated from `app/consensus/synth.py` synthetic bars because this machine has **no network access**. Synthetic edge is not real edge. To produce a tradeable verdict, run the ingest + sweep on your networked machine:

```bash
# Run from echotrader/backend with the venv active.
# 1. On a machine WITH network access, ingest real OHLCV bars
#    (uses app/data/feeders.py -> get_feeder_for_source; crypto via ccxt).
python -m app.consensus.ingest --symbol BTC/USDT --source binance --timeframe 5m \
    --start 2023-01-01 --end 2025-01-01
python -m app.consensus.ingest --symbol BTC/USDT --source binance --timeframe 1m \
    --start 2024-06-01 --end 2025-01-01
python -m app.consensus.ingest --symbol SPY --timeframe 5m \
    --start 2023-01-01 --end 2025-01-01
python -m app.consensus.ingest --symbol GLD --timeframe 5m \
    --start 2023-01-01 --end 2025-01-01
```

Each command prints a data-quality line (bars, gaps, dupes). Then point the sweep
at the ingested bars: in `scripts/run_consensus_phase1.py`, replace the
`synthetic_bars(...)` calls with
`load_bars(db, asset_id, timeframe, start, end, asset_class)` (read side of the
same canonical loader) and feed the resulting bars into `sweep.run_multi`, then
re-run the script to regenerate this report. The verdicts above will only be
trustworthy once they are computed on real, quality-validated market data.
