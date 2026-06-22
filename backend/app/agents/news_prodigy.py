from __future__ import annotations

import datetime as dt
import time
from typing import List, Optional, Dict, Any

from app.core.database import SessionLocal
from app import models
from app.agents.web_tools import duckduckgo_search, fetch_feed_or_scrape
from app.agents._utils import json_safe
from app.agents.media_sources import get_feeds

POSITIVE_WORDS = {
    "surge", "rally", "gain", "gains", "rise", "rises", "rising", "up", "higher",
    "bull", "bullish", "boom", "strong", "growth", "profit", "profits", "beat",
    "outperform", "record", "soar", "jump", "jumped", "recovery", "recover",
    "optimistic", "optimism", "confidence", "expansion", "hiring", "approval",
    "breakthrough", "success", "boost", "boosted", "upside", "rallied",
}

NEGATIVE_WORDS = {
    "fall", "falls", "falling", "drop", "drops", "dropped", "decline", "declines",
    "plunge", "crash", "bear", "bearish", "down", "lower", "loss", "losses", "lose",
    "weak", "recession", "inflation", "cut", "cuts", "fired", "layoff", "layoffs",
    "bankrupt", "bankruptcy", "crisis", "risk", "risks", "concern", "concerns",
    "warn", "warning", "slowdown", "contraction", "fear", "panic", "sell-off",
    "volatile", "volatility", "tension", "war", "sanction", "sanctions",
}

CRITICAL_KEYWORDS = {
    "fed announcement", "interest rate", "fomc", "cpi", "ppi", "unemployment",
    "recession", "debt ceiling", "default", "war", "invasion", "cyberattack",
    "outage", "collapse", "bank run", "emergency",
}

# Default keyword triggers for deeper collection
DEFAULT_TRIGGERS = {
    "fed", "fomc", "cpi", "ppi", "nfp", "unemployment", "recession", "war",
    "invasion", "sanction", "tariff", "oil", "crude", "bitcoin", "btc",
}


class NewsProdigy:
    """Pure data gatherer / summarizer.

    - Scrapes RSS feeds (with Atom fallback) and optional web search.
    - Stores raw headlines with sentiment + severity.
    - Emits a structured digest (NO directional bias, NO trading decisions).
    - Keyword triggers: if a headline matches trigger words, runs a web search
      for related news to deepen the dataset.
    - Rate-limits fetches so the same source isn't hammered every 5 minutes.
    - Deduplicates articles by URL before storage.
    """

    def __init__(
        self,
        feeds: Optional[List[str]] = None,
        triggers: Optional[set[str]] = None,
        enable_web_search: bool = True,
    ):
        self.feeds = feeds or get_feeds()
        self.triggers = triggers or DEFAULT_TRIGGERS
        self.enable_web_search = enable_web_search

    def run(self) -> Dict[str, Any]:
        """Scrape feeds, optionally expand on triggers, store signals, return digest."""
        try:
            print(f"[NewsProdigy] === START RUN === feeds={len(self.feeds)}")
            all_items: List[Dict[str, Any]] = []
            for feed_url in self.feeds:
                try:
                    items = fetch_feed_or_scrape(feed_url, timeout=15)
                    # Enrich with symbol extraction
                    for item in items:
                        item.setdefault("symbol", self._extract_symbol(
                            f"{item.get('title', '')} {item.get('description', '')}"
                        ))
                    all_items.extend(items)
                    print(f"[NewsProdigy] Feed OK: {feed_url} — {len(items)} items")
                except Exception as e:
                    print(f"[NewsProdigy] Feed FAILED: {feed_url} — {e}")
                # Rate-limit: 1-second sleep between feed fetches
                time.sleep(1.0)
            print(f"[NewsProdigy] Total raw items: {len(all_items)}")

            # Deduplicate by URL across all feeds
            seen_urls: set[str] = set()
            unique_items: List[Dict[str, Any]] = []
            for item in all_items:
                url = item.get("url", "")
                if url and url in seen_urls:
                    continue
                if url:
                    seen_urls.add(url)
                unique_items.append(item)
            print(f"[NewsProdigy] Unique items after URL dedup: {len(unique_items)}")

            # Analyze each item (sentiment + severity only — no bias)
            analyzed = []
            triggered_queries: set[str] = set()
            for item in unique_items:
                text = f"{item.get('title', '')} {item.get('description', '')}"
                sentiment, severity = self._analyze_sentiment(text)
                analyzed.append({
                    **item,
                    "sentiment_score": sentiment,
                    "severity": severity,
                })
                # Detect keyword triggers
                if self.enable_web_search and severity in ("high", "critical"):
                    for t in self.triggers:
                        if t in text.lower():
                            triggered_queries.add(t)

            # Deep-dive web search on triggered keywords
            web_results: Dict[str, List[Dict[str, Any]]] = {}
            if self.enable_web_search and triggered_queries:
                for q in triggered_queries:
                    try:
                        web_results[q] = duckduckgo_search(q, max_results=3)
                    except Exception as e:
                        print(f"[NewsProdigy] Web search failed for '{q}': {e}")
                    time.sleep(0.5)

            # Store signals in DB
            print(f"[NewsProdigy] Storing {len(analyzed)} analyzed signals...")
            self._store_signals(analyzed)

            # Build digest
            critical_count = sum(1 for r in analyzed if r["severity"] == "critical")
            high_count = sum(1 for r in analyzed if r["severity"] == "high")

            digest = {
                "headlines_scanned": len(analyzed),
                "critical_count": critical_count,
                "high_count": high_count,
                "triggered_keywords": sorted(triggered_queries),
                "web_expansion": {k: len(v) for k, v in web_results.items()},
                "top_headlines": [
                    {
                        "title": r["title"],
                        "sentiment_score": r["sentiment_score"],
                        "severity": r["severity"],
                        "symbol": r.get("symbol"),
                        "url": r.get("url"),
                    }
                    for r in analyzed[:20]
                ],
                "article_summaries": [
                    {
                        "title": r["title"],
                        "sentiment": r["sentiment_score"],
                        "severity": r["severity"],
                        "symbol": r.get("symbol"),
                        "url": r.get("url"),
                    }
                    for r in analyzed[:50]
                ],
            }

            print(f"[NewsProdigy] === END RUN === headlines={digest['headlines_scanned']} critical={critical_count} high={high_count} triggers={digest['triggered_keywords']}")
            self._store_digest(digest)
            return digest
        except Exception as e:
            print(f"[NewsProdigy] RUN ERROR: {e}")
            import traceback
            traceback.print_exc()
            self._store_digest({"headlines_scanned": 0, "critical_count": 0, "high_count": 0, "triggered_keywords": [], "error": str(e)})
            return {"error": str(e)}

    def _extract_symbol(self, text: str) -> Optional[str]:
        upper = text.upper()
        if "S&P 500" in text or "S&P500" in text or "GSPC" in upper:
            return "SPY"
        if "DOW" in upper or "DJI" in upper:
            return "DIA"
        if "NASDAQ" in upper or "IXIC" in upper:
            return "QQQ"
        if "BITCOIN" in upper or "BTC" in upper:
            return "BTC-USD"
        if "ETHEREUM" in upper or "ETH" in upper:
            return "ETH-USD"
        import re
        m = re.search(r"\$([A-Z]{1,5})\b", text)
        if m:
            return m.group(1)
        return None

    def _analyze_sentiment(self, text: str) -> tuple[float, str]:
        words = text.lower().split()
        pos = sum(1 for w in words if w.strip(".,;:!?") in POSITIVE_WORDS)
        neg = sum(1 for w in words if w.strip(".,;:!?") in NEGATIVE_WORDS)
        total = pos + neg
        if total == 0:
            return 0.0, "low"
        score = (pos - neg) / total
        lower_text = text.lower()
        critical_hits = sum(1 for kw in CRITICAL_KEYWORDS if kw in lower_text)
        if critical_hits >= 2:
            severity = "critical"
        elif critical_hits == 1 or abs(score) > 0.6:
            severity = "high"
        elif abs(score) > 0.3:
            severity = "medium"
        else:
            severity = "low"
        return round(score, 3), severity

    def _store_signals(self, results: List[Dict[str, Any]]):
        db = SessionLocal()
        try:
            cutoff = dt.datetime.utcnow() - dt.timedelta(hours=24)
            recent = (
                db.query(models.NewsSignal.headline, models.NewsSignal.source, models.NewsSignal.url)
                .filter(models.NewsSignal.timestamp >= cutoff)
                .all()
            )
            # Deduplicate by (headline, source) AND by URL
            recent_set = {(h, s) for h, s, _ in recent}
            recent_urls = {u for _, _, u in recent if u}
            inserted = 0
            for r in results:
                title = r.get("title", "")
                source = r.get("source", "")
                url = r.get("url", "")

                # URL dedup check
                if url and url in recent_urls:
                    continue

                # Headline+source dedup check
                key = (title, source)
                if key in recent_set:
                    continue

                ns = models.NewsSignal(
                    timestamp=dt.datetime.utcnow(),
                    symbol=r.get("symbol"),
                    headline=title,
                    sentiment_score=r["sentiment_score"],
                    severity=r["severity"],
                    source=source,
                )
                db.add(ns)
                recent_set.add(key)
                if url:
                    recent_urls.add(url)
                inserted += 1
            db.commit()
            print(f"[NewsProdigy] Inserted {inserted} new signals (deduped {len(results) - inserted})")
        except Exception as e:
            print(f"[NewsProdigy] DB store error: {e}")
        finally:
            db.close()

    def _store_digest(self, digest: Dict[str, Any]):
        db = SessionLocal()
        try:
            report = models.AgentReport(
                agent_type="news_prodigy",
                summary=f"Scanned {digest['headlines_scanned']} headlines. Critical: {digest['critical_count']}, High: {digest['high_count']}. Triggers: {', '.join(digest['triggered_keywords']) or 'none'}.",
                bias_score=50.0,
                confidence=70.0,
                raw_data_json=json_safe(digest),
            )
            db.add(report)
            db.commit()
        except Exception as e:
            print(f"[NewsProdigy] Digest store error: {e}")
        finally:
            db.close()
