from __future__ import annotations

import datetime as dt
from typing import Dict, Any, List

from app.core.database import SessionLocal
from app import models
import time

from app.agents.web_tools import duckduckgo_search
from app.agents._utils import json_safe

# Macro keyword buckets
INFLATION_KWS = {"inflation", "cpi", "ppi", "price index", "cost of living"}
EMPLOYMENT_KWS = {"unemployment", "jobs report", "nfp", "non-farm", "labor"}
RATES_KWS = {"fed", "fomc", "interest rate", "hike", "cut", "pause", "yield curve"}
GROWTH_KWS = {"gdp", "growth", "expansion", "contraction", "recession", "slowdown"}
TRADE_KWS = {"trade deficit", "trade surplus", "import", "export", "supply chain"}

BUCKETS = {
    "inflation": INFLATION_KWS,
    "employment": EMPLOYMENT_KWS,
    "rates": RATES_KWS,
    "growth": GROWTH_KWS,
    "trade": TRADE_KWS,
}


class EconomicAnalyst:
    """Pure data gatherer / summarizer.

    - Scans recent news signals and RSS headlines for macro keyword hits.
    - Optionally performs web searches for trending macro topics.
    - Emits a structured macro keyword digest (NO regime classification, NO trading decisions).
    """

    def __init__(self, lookback_days: int = 7, enable_web_search: bool = True):
        self.lookback_days = lookback_days
        self.enable_web_search = enable_web_search

    def run(self) -> Dict[str, Any]:
        print("[EconomicAnalyst] === START RUN ===")
        db = SessionLocal()
        try:
            cutoff = dt.datetime.utcnow() - dt.timedelta(days=self.lookback_days)
            recent_news = (
                db.query(models.NewsSignal)
                .filter(models.NewsSignal.timestamp >= cutoff)
                .order_by(models.NewsSignal.timestamp.desc())
                .all()
            )
            print(f"[EconomicAnalyst] Scanned {len(recent_news)} news signals since {cutoff.date()}")

            bucket_counts = {k: 0 for k in BUCKETS}
            high_severity_headlines: List[str] = []
            for n in recent_news:
                text = (n.headline or "").lower()
                for bucket, kws in BUCKETS.items():
                    if any(kw in text for kw in kws):
                        bucket_counts[bucket] += 1
                        if n.severity in ("high", "critical"):
                            high_severity_headlines.append(n.headline)

            # Optional web expansion on dominant buckets
            web_results: Dict[str, List[Dict[str, Any]]] = {}
            if self.enable_web_search:
                dominant = [b for b, c in bucket_counts.items() if c >= 3]
                for topic in dominant:
                    try:
                        web_results[topic] = duckduckgo_search(f"macro {topic} news", max_results=3)
                    except Exception as e:
                        print(f"[EconomicAnalyst] Web search failed for '{topic}': {e}")
                    time.sleep(0.5)

            digest = {
                "bucket_counts": bucket_counts,
                "high_severity_headlines": high_severity_headlines[:20],
                "web_expansion": {k: len(v) for k, v in web_results.items()},
                "lookback_days": self.lookback_days,
                "news_signals_scanned": len(recent_news),
            }

            print(f"[EconomicAnalyst] === END RUN === buckets={digest['bucket_counts']} high_sev={len(digest['high_severity_headlines'])}")
            self._store_digest(digest)
            return digest
        except Exception as e:
            print(f"[EconomicAnalyst] RUN ERROR: {e}")
            import traceback
            traceback.print_exc()
            self._store_digest({"bucket_counts": {}, "high_severity_headlines": [], "error": str(e)})
            return {"error": str(e)}
        finally:
            db.close()

    def _store_digest(self, digest: Dict[str, Any]):
        db = SessionLocal()
        try:
            report = models.AgentReport(
                agent_type="economic_analyst",
                summary=f"Macro keyword digest: {digest['bucket_counts']}. High-severity headlines: {len(digest['high_severity_headlines'])}.",
                bias_score=50.0,
                confidence=65.0,
                raw_data_json=json_safe(digest),
            )
            db.add(report)
            db.commit()
        except Exception as e:
            print(f"[EconomicAnalyst] Digest store error: {e}")
        finally:
            db.close()
