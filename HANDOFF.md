# Consensus Bot — Session Handoff

> **Paste the "Opening prompt" at the bottom into a fresh Claude Code session.**
> This file is the durable context. Repo: https://github.com/Victorchatter/consensus
> Project lives at `C:\Users\Victor\echotrader` (the repo IS echotrader; the
> consensus engine is built inside it). Last updated: 2026-06-22.

---

## 1. What this is

The **BTC / multi-asset ensemble-consensus trading bot** from Victor's build
spec. Many independent voters (statistical + Monte Carlo) each vote
long/short/flat each bar; a weighted supermajority fires a trade; sizing is
fractional Kelly. Strict phase gating: **Backtest → Paper → Live**, live OFF by
default behind a typed confirmation.

**Architecture decision (locked):** built **inside EchoTrader**, reusing its
event-driven `BacktestEngine`, paper engine, risk guards, CCXT, and
lightweight-charts — NOT a fresh standalone project. SQLite, not Postgres.

## 2. Current state — Phase 1 (Backtest) + Phase 2 (Paper) DONE

- **75 tests pass.** Run: `cd C:\Users\Victor\echotrader\backend && ./venv/Scripts/python.exe -m pytest tests/ -q`
- The recurring **data-loading bug is root-caused and fixed** (see §4).
- Consensus engine built and verified end-to-end on synthetic data.
- Phase-1 report written: `docs/consensus-phase1-report.md` (honest "NO EDGE"
  verdicts — it's **synthetic data**, see §6).
- **Phase 2 paper trading DONE** (branch `phase2-paper-trading`). Spec/plan in
  `docs/superpowers/{specs,plans}/2026-06-23-consensus-paper-trading*`. Delivered:
  - `DefaultConsensusStrategy` (zero-arg) drops into the bot via class_path loader.
  - `RiskGuard` (`app/execution/guard.py`): strategy-independent kill-switch —
    latches on daily-loss breach, auto-resets at UTC day rollover, blocks opens /
    allows closes, rejects oversized opens. Consulted before every order in the loop.
  - Daily-loss uses an equity baseline snapshotted once per UTC day (independent of
    signal firing), not cumulative PnL.
  - Persistence: `ConsensusSignal` audit table (one row per fired signal) +
    closed `Trade` rows via a paper-engine `on_close` sink.
  - Runnable: `./venv/Scripts/python.exe -m scripts.run_consensus_paper`
    (BTC/USDT 5m paper, source=binance, 24/7, live OFF).
  - Known Phase-3 follow-ups: closed `Trade.entry_time == exit_time` (engine
    on_close carries no entry time); no async e2e test of the latched-blocks-order
    branch (guard itself is fully unit-tested).

## 3. Hard constraints (do NOT violate)

- **Python 3.14.3 on Windows.** No compiled ML libs: **no** sklearn / catboost /
  xgboost / torch / numba. numpy 2.4 + pandas 3.0 are fine.
- **SQLite only** (`database/echotrader.db`, gitignored). No Postgres/Redis.
- Always run python via `./venv/Scripts/python.exe` from `echotrader/backend`.
- Use `127.0.0.1`, not `localhost` (IPv6 resolution). Network I/O off the event
  loop (`asyncio.to_thread`).
- `.env`, `venv/`, `node_modules/`, `*.db` are gitignored — keep it that way
  (the GitHub repo is **PUBLIC**). Never commit secrets.

## 4. The data bug that was fixed (don't reintroduce)

Root cause was a **cluster** from having no normalized bar contract:
1. Feeders returned **tz-aware** timestamps (Yahoo: exchange-local for equities,
   UTC for crypto; Alpaca: UTC) into a **naive** SQLite `PriceBar.timestamp`
   column → mixed wall-clock across asset classes.
2. Dedup compared tz-aware `==` naive → never matched → duplicates / constraint
   trips.
3. yfinance **silently clamps** intraday windows (1m→7d, 5m→60d).
4. Backtests filtered `timestamp <= end_date` with a `date` → lexical compare
   dropped the final day's intraday bars.
5. No CCXT feeder → crypto fell through to Yahoo.

**Fix:** all bars now flow through `app/data/loader.py` (UTC-normalize,
session-aware gap/dup validation, `QualityReport`) + `app/data/timeframe.py`
(canonical vocab). **Consensus reads bars ONLY through `load_bars()`.** Writes go
through `store_timestamp()`. Don't bypass these.

## 5. Key files

```
backend/app/data/
  loader.py        # CANONICAL: to_utc, store_timestamp, normalize_bars,
                   #            validate_bars, load_bars, QualityReport
  timeframe.py     # TIMEFRAME_SECONDS, tf_seconds, is_intraday
  feeders.py       # OHLCVBar, Yahoo/Alpaca/CCXT feeders, get_feeder_for_source
backend/app/consensus/
  base.py          # Voter (incremental observe()->-1|0|+1), ConsensusStrategy
                   # (IS a Strategy -> drops into BacktestEngine), ConsensusConfig
                   # (safety rails), live_trading_allowed(), LIVE_CONFIRMATION_PHRASE
  voters.py        # 13 statistical voters + build_default_voters()
  montecarlo.py    # MonteCarloVoter (bootstrap forward paths)
  weights.py       # compute_weights() = max(0, 2*walk_forward_accuracy - 1)
  sizing.py        # kelly_fraction(), kelly_from_trades() (hard-capped)
  sweep.py         # run_threshold_sweep(), run_multi() (walk-forward, fees+slip)
  report.py        # write_report() -> markdown
  ingest.py        # ingest_bars(), ensure_assets(), DEFAULT_ASSETS, CLI main()
  synth.py         # synthetic_bars() — deterministic, for offline testing
backend/scripts/run_consensus_phase1.py   # generates synth data, runs sweep+report
backend/tests/    # test_data_loader, test_consensus_core, test_voters,
                  # test_montecarlo, test_sizing, test_ingest, test_weights,
                  # test_sweep, test_report
docs/consensus-phase1-report.md           # the Phase-1 deliverable
```

## 6. Synthetic vs real data (IMPORTANT)

The build machine has **no network**, so the report is from synthetic bars and
shows **no tradeable edge — that is expected**, not a result about real markets.
To get a real verdict (run on a networked machine):
```bash
cd echotrader/backend   # venv active
python -m app.consensus.ingest --symbol BTC/USDT --source binance --timeframe 5m --start 2023-01-01 --end 2025-01-01
python -m app.consensus.ingest --symbol SPY --timeframe 5m --start 2023-01-01 --end 2025-01-01
python -m app.consensus.ingest --symbol GLD --timeframe 5m --start 2023-01-01 --end 2025-01-01
# then swap synthetic_bars(...) -> load_bars(db, asset_id, tf, start, end, asset_class)
# in scripts/run_consensus_phase1.py and re-run it to regenerate the report.
```

## 7. Safety rails status (Section 1 of the spec)

- `ConsensusConfig.live_trading_enabled = False` by default. ✅
- `live_trading_allowed(config, typed_phrase, paper_days)` requires ALL of:
  config flag true + exact phrase `"I ENABLE LIVE TRADING"` + paper-minimum
  (14d) met. ✅ (gate exists; the execution loop that CALLS it is Phase 3.)
- `max_position_pct`, `max_daily_loss_pct`, `kelly_fraction` are config
  constants. ✅ **Execution-layer enforcement done in Phase 2** — `RiskGuard`
  (`app/execution/guard.py`) is consulted by the bot before every order,
  independent of the strategy.

## 8. What's next (Phase 3, in priority order)

1. ✅ **Paper-trading loop** — DONE (Phase 2). See §2.
2. ✅ **Execution-layer kill-switch / max-daily-loss / position cap** — DONE (Phase 2).
3. **Run the 14-day paper soak** — actually run `scripts.run_consensus_paper` on a
   networked machine ≥14 days; inspect `consensus_signals` + closed `trades` tables.
   This is a gate, not code: live is unreachable until it completes.
4. **Frontend consensus-meter** — live long/short/flat meter across the ~14
   voters, equity/drawdown charts, trade log with full vote reasoning (join
   `consensus_signals` to `trades` on asset+timestamp), prominent phase indicator
   showing LIVE = OFF. Stack: React/Vite + lightweight-charts (already in frontend).
5. **Compare paper vs backtest** — large divergence blocks progression to live.
   Needs real per-trade `entry_time` (currently `== exit_time`; add an entry
   timestamp to the paper engine `on_close` payload first).

**Deferred:** ML voters (CatBoost/XGBoost) — needs a separate Python 3.12 venv
or verified 3.14 wheels; the spec itself says ML may add no edge, so prove the
harness on real data first.

## 9. Open question before live (spec §12)

**Which exchange will actually trade — Binance, Kraken, Coinbase?** Determines
CCXT config + API key setup. Confirm before wiring Phase 3 execution.

## 10. Notes / gotchas

- EchoTrader has its OWN pre-existing bugs (chart "Load History" no-op,
  Intelligence page empty) — these are NOT consensus work; ignore unless asked.
- Process used last session: `brainstorming` → `systematic-debugging` (for the
  data bug) → a Workflow of subagents with a verify→fix loop. Ultracode/ponytail
  were on.
- Memory file: `project_consensus` (in Claude memory) tracks this across sessions.

---

## Opening prompt (paste into the next session)

> Continue the **Consensus** trading bot. Read `HANDOFF.md` at the repo root
> first — it has full context. Project: `C:\Users\Victor\echotrader` (repo
> github.com/Victorchatter/consensus). Phase 1 (backtest + data-loader fix) is
> done and pushed; 60 tests pass via
> `cd backend && ./venv/Scripts/python.exe -m pytest tests/ -q`.
>
> I want to start **Phase 2: paper trading**. Wire `ConsensusStrategy` into
> EchoTrader's paper engine + bot loop, log per-trade vote breakdowns to the DB,
> and add the execution-layer kill-switch / max-daily-loss / position cap
> (enforced independent of the strategy). Keep the hard constraints (Python 3.14,
> no compiled ML libs, SQLite, live OFF by default). Brainstorm the design with
> me before building, then use subagents + a verify loop like last time.
