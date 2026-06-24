# EchoTrader Consensus — Phase 1 Report

_Run date: {{RUN_DATE}}_

Walk-forward consensus-threshold sweep with realistic commissions and slippage applied to every fill. **All numbers below are from SYNTHETIC data** and exist to validate the harness, not to justify trades. See _How to regenerate with REAL data_ at the bottom.

## Summary: which timeframe wins per asset

- **BTC/USDT** (crypto): **NO EDGE on any timeframe** (1h: Sharpe -0.026, 5m: Sharpe -0.309). Best available is 1h but Sharpe <= 0.
- **SPY** (etf): **1h wins** (1h: Sharpe 0.191, 5m: Sharpe -0.228).
- **GLD** (commodity): **1h wins** (1h: Sharpe 0.113, 5m: Sharpe -0.416).

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

### BTC/USDT — crypto @ 1h

| Threshold | Return % | Sharpe | Sortino | MaxDD % | Win % | #Trades |
|---:|---:|---:|---:|---:|---:|---:|
| 0.50 | -23.76 | -0.2069 | 28542678921.5834 | 4.21 | 56.7% | 534 |
| 0.60 | -9.71 | -0.1076 | 28542678921.6095 | 3.45 | 60.2% | 384 |
| 0.70 | -6.74 | -0.0632 | 8913866946.7297 | 3.15 | 66.1% | 233 |
| 0.80 *(best)* | -3.23 | -0.0258 | 27667456665.1762 | 3.13 | 67.4% | 141 |
| 0.90 | -6.12 | -0.0377 | 27667456665.1211 | 3.13 | 62.7% | 75 |

**Best threshold:** 0.80

**Data quality:** 39240 bars, 259 walk-forward folds (train 300 / test 150 per fold), commission 0.100%, slippage 0.050%.

**Verdict: NO EDGE.** Best threshold 0.80 for BTC/USDT @ 1h yields Sharpe -0.026 (<= 0) over 141 out-of-sample trades, net total return -3.23%. After realistic fees and slippage there is **no tradeable edge** here — do not deploy capital on this configuration.

### SPY — etf @ 1h

| Threshold | Return % | Sharpe | Sortino | MaxDD % | Win % | #Trades |
|---:|---:|---:|---:|---:|---:|---:|
| 0.50 | 0.86 | 0.0462 | 0.3029 | 1.10 | 43.2% | 37 |
| 0.60 | 1.54 | 0.0983 | 0.2992 | 1.10 | 50.0% | 28 |
| 0.70 *(best)* | 2.18 | 0.1908 | 0.4058 | 1.09 | 47.4% | 19 |
| 0.80 | -0.72 | -0.0712 | 0.0988 | 1.06 | 46.7% | 15 |
| 0.90 | 0.28 | 0.0975 | 0.1567 | 1.06 | 54.5% | 11 |

**Best threshold:** 0.70

**Data quality:** 4032 bars, 24 walk-forward folds (train 300 / test 150 per fold), commission 0.050%, slippage 0.050%.

**Verdict: MARGINAL EDGE.** Best threshold 0.70 for SPY @ 1h produces a positive out-of-sample Sharpe of 0.191 across 19 trades, net total return 2.18% after fees + slippage. This is a marginal signal on synthetic data only — it must be re-run on REAL ingested bars before any capital is risked.

### GLD — commodity @ 1h

| Threshold | Return % | Sharpe | Sortino | MaxDD % | Win % | #Trades |
|---:|---:|---:|---:|---:|---:|---:|
| 0.50 | 1.37 | 0.0910 | 0.2300 | 2.39 | 52.2% | 23 |
| 0.60 *(best)* | 0.79 | 0.1129 | 0.2290 | 1.12 | 56.2% | 16 |
| 0.70 | 0.43 | 0.0462 | 0.1838 | 1.11 | 55.6% | 9 |
| 0.80 | -0.74 | -0.0267 | 0.0710 | 1.11 | 42.9% | 7 |
| 0.90 | -1.68 | -0.1562 | -0.0733 | 1.11 | 16.7% | 6 |

**Best threshold:** 0.60

**Data quality:** 3476 bars, 21 walk-forward folds (train 300 / test 150 per fold), commission 0.030%, slippage 0.050%.

**Verdict: MARGINAL EDGE.** Best threshold 0.60 for GLD @ 1h produces a positive out-of-sample Sharpe of 0.113 across 16 trades, net total return 0.79% after fees + slippage. This is a marginal signal on synthetic data only — it must be re-run on REAL ingested bars before any capital is risked.

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
