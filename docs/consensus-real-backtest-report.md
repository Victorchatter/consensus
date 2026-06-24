# EchoTrader Consensus — Phase 1 Report

_Run date: {{RUN_DATE}}_

Walk-forward consensus-threshold sweep with realistic commissions and slippage applied to every fill. **All numbers below are from SYNTHETIC data** and exist to validate the harness, not to justify trades. See _How to regenerate with REAL data_ at the bottom.

## Summary: which timeframe wins per asset

- **BTC/USDT** (crypto): **NO EDGE on any timeframe** (5m: Sharpe -0.309). Best available is 5m but Sharpe <= 0.
- **SPY** (etf): **NO EDGE on any timeframe** (5m: Sharpe -0.228). Best available is 5m but Sharpe <= 0.
- **GLD** (commodity): **NO EDGE on any timeframe** (5m: Sharpe -0.416). Best available is 5m but Sharpe <= 0.

## Per-dataset threshold sweeps

### BTC/USDT — crypto @ 5m

| Threshold | Return % | Sharpe | Sortino | MaxDD % | Win % | #Trades |
|---:|---:|---:|---:|---:|---:|---:|
| 0.50 | -98.87 | -1.0630 | 9176723480.2658 | 2.35 | 31.4% | 5790 |
| 0.60 | -95.96 | -0.8191 | -38106791.3283 | 2.17 | 33.0% | 4125 |
| 0.70 | -90.75 | -0.6398 | 1092775558.0886 | 2.17 | 34.0% | 3021 |
| 0.80 | -79.32 | -0.4619 | -1021945259.7763 | 1.69 | 35.4% | 2030 |
| 0.90 *(best)* | -62.99 | -0.3086 | -1021945259.6928 | 1.68 | 35.3% | 1307 |

**Best threshold:** 0.90

**Data quality:** 470865 bars, 3137 walk-forward folds (train 300 / test 150 per fold), commission 0.100%, slippage 0.050%.

**Verdict: NO EDGE.** Best threshold 0.90 for BTC/USDT @ 5m yields Sharpe -0.309 (<= 0) over 1307 out-of-sample trades, net total return -62.99%. After realistic fees and slippage there is **no tradeable edge** here — do not deploy capital on this configuration.

### SPY — etf @ 5m

| Threshold | Return % | Sharpe | Sortino | MaxDD % | Win % | #Trades |
|---:|---:|---:|---:|---:|---:|---:|
| 0.50 | -2.13 | -1.4594 | -1.1617 | 0.41 | 23.5% | 34 |
| 0.60 | -1.86 | -1.2367 | -1.0372 | 0.41 | 26.9% | 26 |
| 0.70 | -1.45 | -1.0433 | -0.8933 | 0.34 | 22.7% | 22 |
| 0.80 | -0.94 | -0.6078 | -0.5144 | 0.34 | 18.8% | 16 |
| 0.90 *(best)* | -0.35 | -0.2278 | -0.1822 | 0.30 | 22.2% | 9 |

**Best threshold:** 0.90

**Data quality:** 3042 bars, 18 walk-forward folds (train 300 / test 150 per fold), commission 0.050%, slippage 0.050%.

**Verdict: NO EDGE.** Best threshold 0.90 for SPY @ 5m yields Sharpe -0.228 (<= 0) over 9 out-of-sample trades, net total return -0.35%. After realistic fees and slippage there is **no tradeable edge** here — do not deploy capital on this configuration.

### GLD — commodity @ 5m

| Threshold | Return % | Sharpe | Sortino | MaxDD % | Win % | #Trades |
|---:|---:|---:|---:|---:|---:|---:|
| 0.50 | -1.92 | -0.7217 | -0.4761 | 0.75 | 37.0% | 46 |
| 0.60 | -2.28 | -0.8594 | -0.6511 | 0.75 | 30.6% | 36 |
| 0.70 | -1.03 | -0.6144 | -0.4906 | 0.27 | 8.3% | 12 |
| 0.80 | -0.85 | -0.4600 | -0.3578 | 0.27 | 14.3% | 7 |
| 0.90 *(best)* | -0.69 | -0.4156 | -0.3272 | 0.24 | 0.0% | 5 |

**Best threshold:** 0.90

**Data quality:** 3042 bars, 18 walk-forward folds (train 300 / test 150 per fold), commission 0.030%, slippage 0.050%.

**Verdict: NO EDGE.** Best threshold 0.90 for GLD @ 5m yields Sharpe -0.416 (<= 0) over 5 out-of-sample trades, net total return -0.69%. After realistic fees and slippage there is **no tradeable edge** here — do not deploy capital on this configuration.

## How to regenerate with REAL data

Everything above is generated from `app/consensus/synth.py` synthetic bars because this machine has **no network access**. Synthetic edge is not real edge. To produce a tradeable verdict, run the ingest + sweep on your networked machine:

```bash
# 1. On a machine WITH network access, ingest real OHLCV bars
#    (uses app/data/feeders.py -> get_feeder_for_source).
python -m app.consensus.ingest --symbol BTC-USD --timeframe 5m \
    --start 2023-01-01 --end 2025-01-01
python -m app.consensus.ingest --symbol BTC-USD --timeframe 1m \
    --start 2024-06-01 --end 2025-01-01
python -m app.consensus.ingest --symbol SPY --timeframe 5m \
    --start 2023-01-01 --end 2025-01-01
python -m app.consensus.ingest --symbol GLD --timeframe 5m \
    --start 2023-01-01 --end 2025-01-01

# 2. Re-run the sweep against the ingested bars (loaded via
#    app/data/loader.py load_bars) instead of synthetic_bars,
#    then regenerate this report:
python scripts/run_consensus_phase1.py --real
```

Swap the `synthetic_bars(...)` calls in `scripts/run_consensus_phase1.py` for `load_bars(db, asset_id, timeframe, start, end, asset_class)` and pass the resulting bars into `sweep.run_multi`. The verdicts above will only be trustworthy once they are computed on real, quality-validated market data.
