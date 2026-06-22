from __future__ import annotations

import datetime as dt
from typing import Dict, Any, List

from app.core.database import SessionLocal
from app import models
import time

from app.agents.web_tools import duckduckgo_search
from app.agents._utils import json_safe

# Geopolitical keyword buckets
WAR_KWS = {"war", "invasion", "attack", "missile", "airstrike", "bombing", "conflict", "hostilities"}
SANCTION_KWS = {"sanction", "embargo", "trade war", "tariff", "restrictions"}
ELECTION_KWS = {"election", "vote", "ballot", "campaign", "polling", "referendum"}
POLICY_KWS = {"legislation", "bill", "congress", "parliament", "policy", "regulation", "debt ceiling"}
CRISIS_KWS = {"crisis", "emergency", "shutdown", "default", "gridlock", "instability"}
DIPLOMACY_KWS = {"summit", "treaty", "negotiation", "diplomatic", "ceasefire", "peace"}

BUCKETS = {
    "war": WAR_KWS,
    "sanction": SANCTION_KWS,
    "election": ELECTION_KWS,
    "policy": POLICY_KWS,
    "crisis": CRISIS_KWS,
    "diplomacy": DIPLOMACY_KWS,
}


class PoliticalAnalyst:
    """Pure data gatherer / summarizer.

    - Scans recent news signals for geopolitical keyword hits.
    - Optionally performs web searches on dominant topics.
    - Emits a structured geopolitical keyword digest (NO risk score, NO trading decisions).
    """

    def __init__(self, lookback_days: int = 3, enable_web_search: bool = True):
        self.lookback_days = lookback_days
        self.enable_web_search = enable_web_search

    def run(self) -> Dict[str, Any]:
        print("[PoliticalAnalyst] === START RUN ===")
        db = SessionLocal()
        try:
            cutoff = dt.datetime.utcnow() - dt.timedelta(days=self.lookback_days)
            recent_news = (
                db.query(models.NewsSignal)
                .filter(models.NewsSignal.timestamp >= cutoff)
                .order_by(models.NewsSignal.timestamp.desc())
                .all()
            )
            print(f"[PoliticalAnalyst] Scanned {len(recent_news)} news signals since {cutoff.date()}")

            bucket_counts = {k: 0 for k in BUCKETS}
            high_severity_headlines: List[str] = []
            for n in recent_news:
                text = (n.headline or "").lower()
                for bucket, kws in BUCKETS.items():
                    if any(kw in text for kw in kws):
                        bucket_counts[bucket] += 1
                        if n.severity in ("high", "critical"):
                            high_severity_headlines.append(n.headline)

            # Optional web expansion
            web_results: Dict[str, List[Dict[str, Any]]] = {}
            if self.enable_web_search:
                dominant = [b for b, c in bucket_counts.items() if c >= 2]
                for topic in dominant:
                    try:
                        web_results[topic] = duckduckgo_search(f"geopolitical {topic} news", max_results=3)
                    except Exception as e:
                        print(f"[PoliticalAnalyst] Web search failed for '{topic}': {e}")
                    time.sleep(0.5)

            digest = {
                "bucket_counts": bucket_counts,
                "high_severity_headlines": high_severity_headlines[:20],
                "web_expansion": {k: len(v) for k, v in web_results.items()},
                "lookback_days": self.lookback_days,
                "news_signals_scanned": len(recent_news),
            }

            print(f"[PoliticalAnalyst] === END RUN === buckets={digest['bucket_counts']} high_sev={len(digest['high_severity_headlines'])}")
            self._store_digest(digest)
            return digest
        except Exception as e:
            print(f"[PoliticalAnalyst] RUN ERROR: {e}")
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
                agent_type="political_analyst",
                summary=f"Geopolitical digest: {digest['bucket_counts']}. High-severity headlines: {len(digest['high_severity_headlines'])}.",
                bias_score=50.0,
                confidence=min(100, 40 + sum(digest['bucket_counts'].values())),
                raw_data_json=json_safe(digest),
            )
            db.add(report)
            db.commit()
        except Exception as e:
            print(f"[PoliticalAnalyst] Digest store error: {e}")
        finally:
            db.close()
