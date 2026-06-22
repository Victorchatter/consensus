from __future__ import annotations

import datetime as dt
from typing import Dict, Any, List, Optional

from app.core.database import SessionLocal
from app import models
from app.data.indicators import sma, ema, rsi, bollinger, macd
from app.data.feeders import get_feeder_for_source, OHLCVBar
from app.agents._utils import json_safe


class FinancialMarketAnalyst:
    """Pure data gatherer / summarizer.

    - Computes raw technical indicator values per asset.
    - Emits structured technical snapshots (NO bias, NO trading decisions).
    - Uses DB-first with feeder fallback.
    """

    def __init__(self, asset_ids: Optional[List[int]] = None, window: int = 20):
        self.asset_ids = asset_ids
        self.window = window

    def run(self) -> Dict[str, Any]:
        print("[FinancialMarketAnalyst] === START RUN ===")
        db = SessionLocal()
        try:
            assets = self.asset_ids or [a.id for a in db.query(models.Asset).filter(models.Asset.is_active == True).all()]
            print(f"[FinancialMarketAnalyst] Assets to analyze: {len(assets)}")
            if not assets:
                print("[FinancialMarketAnalyst] No active assets.")
                return {"snapshots": [], "summary": "No active assets to analyze."}

            snapshots = []
            for asset_id in assets:
                asset = db.query(models.Asset).get(asset_id)
                if not asset:
                    continue
                try:
                    snap = self._snapshot_asset(asset)
                    if snap:
                        snapshots.append(snap)
                        print(f"[FinancialMarketAnalyst] Snapshot OK: {asset.symbol} bars={snap['bar_count']} rsi={snap['indicators'].get('rsi')}")
                    else:
                        print(f"[FinancialMarketAnalyst] Snapshot SKIP: {asset.symbol} — not enough bars")
                except Exception as e:
                    print(f"[FinancialMarketAnalyst] Snapshot ERROR for {asset.symbol}: {e}")

            digest = {
                "snapshots": snapshots,
                "summary": f"Computed technical snapshots for {len(snapshots)} assets.",
            }
            print(f"[FinancialMarketAnalyst] === END RUN === snapshots={len(snapshots)}")
            self._store_digest(digest)
            return digest
        except Exception as e:
            print(f"[FinancialMarketAnalyst] RUN ERROR: {e}")
            import traceback
            traceback.print_exc()
            self._store_digest({"snapshots": [], "summary": f"ERROR: {e}", "error": str(e)})
            return {"error": str(e)}
        finally:
            db.close()

    def _snapshot_asset(self, asset: models.Asset) -> Optional[Dict[str, Any]]:
        db = SessionLocal()
        try:
            end = dt.date.today()
            start = end - dt.timedelta(days=60)

            # DB-first
            db_bars = (
                db.query(models.PriceBar)
                .filter(
                    models.PriceBar.asset_id == asset.id,
                    models.PriceBar.timeframe == "1d",
                    models.PriceBar.timestamp >= start,
                )
                .order_by(models.PriceBar.timestamp.asc())
                .all()
            )
            bars = db_bars
            if len(bars) < self.window + 10:
                try:
                    feeder = get_feeder_for_source(asset.data_source or "yahoo")
                    fetched = feeder.fetch_historical(asset.symbol, start, end, "1d")
                    if len(fetched) >= self.window + 10:
                        bars = fetched
                except Exception as e:
                    print(f"[FinancialAnalyst] Feeder failed for {asset.symbol}: {e}")

            if len(bars) < self.window + 10:
                return None

            if isinstance(bars[0], models.PriceBar):
                ohlcv = [OHLCVBar(b.timestamp, b.open, b.high, b.low, b.close, b.volume) for b in bars]
            else:
                ohlcv = [OHLCVBar(b.timestamp, b.open, b.high, b.low, b.close, b.volume) for b in bars]
        finally:
            db.close()

        sma_vals = sma(ohlcv, self.window)
        ema_vals = ema(ohlcv, self.window)
        rsi_vals = rsi(ohlcv, 14)
        bb_vals = bollinger(ohlcv, 20)
        macd_vals = macd(ohlcv)

        latest_close = bars[-1].close
        latest_sma = sma_vals[-1]["value"] if sma_vals else None
        latest_ema = ema_vals[-1]["value"] if ema_vals else None
        latest_rsi = rsi_vals[-1]["value"] if rsi_vals else None
        latest_bb = bb_vals[-1] if bb_vals else None
        latest_macd = macd_vals[-1] if macd_vals else None

        return {
            "asset_id": asset.id,
            "symbol": asset.symbol,
            "price": latest_close,
            "indicators": {
                "sma": latest_sma,
                "ema": latest_ema,
                "rsi": latest_rsi,
                "bollinger": latest_bb,
                "macd": latest_macd,
            },
            "indicator_series": {
                "sma": [v["value"] for v in sma_vals],
                "ema": [v["value"] for v in ema_vals],
                "rsi": [v["value"] for v in rsi_vals],
            },
            "bar_count": len(bars),
        }

    def _store_digest(self, digest: Dict[str, Any]):
        db = SessionLocal()
        try:
            report = models.AgentReport(
                agent_type="financial_analyst",
                summary=digest["summary"],
                bias_score=50.0,
                confidence=80.0,
                raw_data_json=json_safe(digest),
            )
            db.add(report)
            db.commit()
        except Exception as e:
            print(f"[FinancialAnalyst] Digest store error: {e}")
        finally:
            db.close()
