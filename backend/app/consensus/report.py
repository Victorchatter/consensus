"""
Phase-1 consensus report renderer.

Takes a list of `run_threshold_sweep` result dicts and renders an honest
Markdown report: one section per (symbol / asset_class / timeframe) with a
threshold-sweep table, the chosen best threshold, a data-quality line, and a
plain-spoken verdict on whether any edge survives fees + slippage and which
timeframe wins per asset.

No network, no live data — purely formats dicts produced by the sweep.
"""
from __future__ import annotations

from typing import Any, Dict, List, Optional, Tuple


# ── small helpers ─────────────────────────────────────────────────────────────


def _fmt(x: Any, nd: int = 2) -> str:
    try:
        return f"{float(x):.{nd}f}"
    except (TypeError, ValueError):
        return str(x)


def _pct(x: Any, nd: int = 2) -> str:
    try:
        return f"{float(x) * 100:.{nd}f}%"
    except (TypeError, ValueError):
        return str(x)


def _best_row(result: Dict[str, Any]) -> Optional[Dict[str, Any]]:
    """Return the per-threshold row for the result's best_threshold."""
    per = result.get("per_threshold", {}) or {}
    best = result.get("best_threshold")
    if best is None:
        return None
    row = per.get(str(best))
    if row is not None:
        return row
    # tolerate float-key formatting mismatch
    for v in per.values():
        try:
            if abs(float(v.get("threshold")) - float(best)) < 1e-9:
                return v
        except (TypeError, ValueError):
            continue
    return None


def _section_table(result: Dict[str, Any]) -> str:
    """Render the threshold-sweep markdown table for one result."""
    per = result.get("per_threshold", {}) or {}
    # sort by numeric threshold
    rows = sorted(per.values(), key=lambda r: float(r.get("threshold", 0.0)))

    header = (
        "| Threshold | Return % | Sharpe | Sortino | MaxDD % | Win % | #Trades |\n"
        "|---:|---:|---:|---:|---:|---:|---:|\n"
    )
    lines = [header.rstrip("\n")]
    best = result.get("best_threshold")
    for r in rows:
        t = float(r.get("threshold", 0.0))
        marker = " *(best)*" if best is not None and abs(t - float(best)) < 1e-9 else ""
        lines.append(
            "| {thr}{mark} | {ret} | {shp} | {srt} | {dd} | {win} | {nt} |".format(
                thr=_fmt(t, 2),
                mark=marker,
                ret=_fmt(r.get("total_return_pct", 0.0), 2),
                shp=_fmt(r.get("sharpe", 0.0), 4),
                srt=_fmt(r.get("sortino", 0.0), 4),
                dd=_fmt(r.get("max_drawdown_pct", 0.0), 2),
                win=_pct(r.get("win_rate", 0.0), 1),
                nt=int(r.get("n_trades", 0) or 0),
            )
        )
    return "\n".join(lines)


def _verdict(result: Dict[str, Any]) -> str:
    """Honest per-section verdict on edge after fees + slippage."""
    sym = result.get("symbol", "?")
    tf = result.get("timeframe", "?")
    row = _best_row(result)
    if row is None:
        return (
            f"**Verdict:** No usable result for {sym} @ {tf} — the sweep produced "
            f"no folds. Treat as **no edge**."
        )

    sharpe = float(row.get("sharpe", 0.0) or 0.0)
    ret = float(row.get("total_return_pct", 0.0) or 0.0)
    nt = int(row.get("n_trades", 0) or 0)
    best_t = result.get("best_threshold")

    if nt == 0:
        return (
            f"**Verdict:** At the best threshold ({_fmt(best_t, 2)}) the consensus "
            f"never traded {sym} @ {tf} after costs — **no edge** to report."
        )

    if sharpe <= 0.0:
        return (
            f"**Verdict: NO EDGE.** Best threshold {_fmt(best_t, 2)} for {sym} @ {tf} "
            f"yields Sharpe {_fmt(sharpe, 3)} (<= 0) over {nt} out-of-sample trades, "
            f"net total return {_fmt(ret, 2)}%. After realistic fees and slippage "
            f"there is **no tradeable edge** here — do not deploy capital on this "
            f"configuration."
        )

    strength = "marginal" if sharpe < 0.5 else ("modest" if sharpe < 1.0 else "meaningful")
    return (
        f"**Verdict: {strength.upper()} EDGE.** Best threshold {_fmt(best_t, 2)} for "
        f"{sym} @ {tf} produces a positive out-of-sample Sharpe of {_fmt(sharpe, 3)} "
        f"across {nt} trades, net total return {_fmt(ret, 2)}% after fees + slippage. "
        f"This is a {strength} signal on synthetic data only — it must be re-run on "
        f"REAL ingested bars before any capital is risked."
    )


def _asset_timeframe_winner(results: List[Dict[str, Any]]) -> str:
    """Cross-section summary: which timeframe wins per asset (1m vs 5m)."""
    # group results by (symbol, asset_class)
    groups: Dict[Tuple[str, str], List[Dict[str, Any]]] = {}
    for r in results:
        key = (str(r.get("symbol", "?")), str(r.get("asset_class", "?")))
        groups.setdefault(key, []).append(r)

    lines: List[str] = []
    for (sym, ac), rs in groups.items():
        # collect best sharpe per timeframe
        tf_best: Dict[str, float] = {}
        for r in rs:
            tf = str(r.get("timeframe", "?"))
            row = _best_row(r)
            sh = float(row.get("sharpe", 0.0) or 0.0) if row else 0.0
            tf_best[tf] = max(tf_best.get(tf, float("-inf")), sh)

        if not tf_best:
            continue

        # determine winner
        win_tf = max(tf_best, key=lambda k: tf_best[k])
        win_sh = tf_best[win_tf]

        detail = ", ".join(
            f"{tf}: Sharpe {_fmt(sh, 3)}" for tf, sh in sorted(tf_best.items())
        )

        if win_sh <= 0.0:
            lines.append(
                f"- **{sym}** ({ac}): **NO EDGE on any timeframe** ({detail}). "
                f"Best available is {win_tf} but Sharpe <= 0."
            )
        elif len(tf_best) == 1:
            lines.append(
                f"- **{sym}** ({ac}): only {win_tf} was swept ({detail}); "
                f"positive Sharpe but no 1m-vs-5m comparison available."
            )
        else:
            lines.append(
                f"- **{sym}** ({ac}): **{win_tf} wins** ({detail})."
            )
    return "\n".join(lines) if lines else "- (no results)"


# ── public API ────────────────────────────────────────────────────────────────


def write_report(results: List[Dict[str, Any]], out_path: str) -> str:
    """Render the Phase-1 Markdown report, write it to `out_path`, and return it.

    `results` is a list of `run_threshold_sweep` dicts.
    """
    parts: List[str] = []

    parts.append("# EchoTrader Consensus — Phase 1 Report")
    parts.append("")
    parts.append("_Run date: {{RUN_DATE}}_")
    parts.append("")
    parts.append(
        "Walk-forward consensus-threshold sweep with realistic commissions and "
        "slippage applied to every fill. **All numbers below are from SYNTHETIC "
        "data** and exist to validate the harness, not to justify trades. See "
        "_How to regenerate with REAL data_ at the bottom."
    )
    parts.append("")

    # ── cross-asset summary ──
    parts.append("## Summary: which timeframe wins per asset")
    parts.append("")
    parts.append(_asset_timeframe_winner(results))
    parts.append("")

    # ── per-section detail ──
    parts.append("## Per-dataset threshold sweeps")
    parts.append("")
    for r in results:
        sym = r.get("symbol", "?")
        ac = r.get("asset_class", "?")
        tf = r.get("timeframe", "?")
        n_bars = r.get("n_bars", 0)
        n_folds = r.get("n_folds", 0)
        best_t = r.get("best_threshold")

        parts.append(f"### {sym} — {ac} @ {tf}")
        parts.append("")
        parts.append(_section_table(r))
        parts.append("")
        parts.append(f"**Best threshold:** {_fmt(best_t, 2)}")
        parts.append("")

        dq = r.get("data_quality", {}) or {}
        parts.append(
            "**Data quality:** {nb} bars, {nf} walk-forward folds "
            "(train {tr} / test {te} per fold), commission {com}, "
            "slippage {slp}.".format(
                nb=n_bars,
                nf=n_folds,
                tr=dq.get("train_size", "?"),
                te=dq.get("test_size", "?"),
                com=_pct(dq.get("commission_pct", 0.0), 3),
                slp=_pct(dq.get("slippage_pct", 0.0), 3),
            )
        )
        parts.append("")
        parts.append(_verdict(r))
        parts.append("")

    # ── honesty / regeneration section ──
    parts.append("## How to regenerate with REAL data")
    parts.append("")
    parts.append(
        "Everything above is generated from `app/consensus/synth.py` synthetic "
        "bars because this machine has **no network access**. Synthetic edge is "
        "not real edge. To produce a tradeable verdict, run the ingest + sweep on "
        "your networked machine:"
    )
    parts.append("")
    parts.append("```bash")
    parts.append("# 1. On a machine WITH network access, ingest real OHLCV bars")
    parts.append("#    (uses app/data/feeders.py -> get_feeder_for_source).")
    parts.append("python -m app.consensus.ingest --symbol BTC-USD --timeframe 5m \\")
    parts.append("    --start 2023-01-01 --end 2025-01-01")
    parts.append("python -m app.consensus.ingest --symbol BTC-USD --timeframe 1m \\")
    parts.append("    --start 2024-06-01 --end 2025-01-01")
    parts.append("python -m app.consensus.ingest --symbol SPY --timeframe 5m \\")
    parts.append("    --start 2023-01-01 --end 2025-01-01")
    parts.append("python -m app.consensus.ingest --symbol GLD --timeframe 5m \\")
    parts.append("    --start 2023-01-01 --end 2025-01-01")
    parts.append("")
    parts.append("# 2. Re-run the sweep against the ingested bars (loaded via")
    parts.append("#    app/data/loader.py load_bars) instead of synthetic_bars,")
    parts.append("#    then regenerate this report:")
    parts.append("python scripts/run_consensus_phase1.py --real")
    parts.append("```")
    parts.append("")
    parts.append(
        "Swap the `synthetic_bars(...)` calls in `scripts/run_consensus_phase1.py` "
        "for `load_bars(db, asset_id, timeframe, start, end, asset_class)` and pass "
        "the resulting bars into `sweep.run_multi`. The verdicts above will only be "
        "trustworthy once they are computed on real, quality-validated market data."
    )
    parts.append("")

    text = "\n".join(parts)

    with open(out_path, "w", encoding="utf-8") as fh:
        fh.write(text)

    return text


__all__ = ["write_report"]
