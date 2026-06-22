from __future__ import annotations

import datetime as dt
import time
from typing import Dict, Any, List, Optional

from app.core.database import SessionLocal
from app import models
from app.agents.web_tools import duckduckgo_search, fetch_html, extract_text_from_html
from app.agents._utils import json_safe
from app.agents.news_prodigy import NewsProdigy
from app.agents.financial_analyst import FinancialMarketAnalyst
from app.agents.economic_analyst import EconomicAnalyst
from app.agents.political_analyst import PoliticalAnalyst


# Keyword triggers that cause the CEO to perform deeper web research
CEO_TRIGGERS = {
    "crash", "recession", "war", "invasion", "fed emergency", "bank run",
    "default", "debt ceiling", "cyberattack", "outage", "collapse",
    "tariff", "sanction", "oil spike", "inflation shock",
}

# Thresholds for qualitative decisions
RISK_CRITICAL_THRESHOLD = 70
RISK_HIGH_THRESHOLD = 50
RISK_MEDIUM_THRESHOLD = 25
CONFIDENCE_MIN = 40


class CEOAgent:
    """The Chief Executive Officer agent.

    - Runs sub-agents as pure data gatherers.
    - Performs ALL qualitative analysis: regime, risk, directional bias.
    - Makes trading decisions and can execute paper trades directly.
    - Has full internet access for fact-checking and cross-referencing.
    - Keyword triggers: if triggered keywords appear, runs deeper web research.
    - Paperclip heartbeat: every 4-6 hours produces a friendly market check-in.
    """

    def __init__(
        self,
        enable_trade_execution: bool = True,
        paper_only: bool = True,
        heartbeat_hours: int = 4,
    ):
        self.enable_trade_execution = enable_trade_execution
        self.paper_only = paper_only
        self.heartbeat_hours = heartbeat_hours
        self._last_heartbeat: Optional[dt.datetime] = None

    def run(self) -> Dict[str, Any]:
        """Execute one full CEO cycle: gather, analyze, decide, act, heartbeat."""
        try:
            print("[CEOAgent] === START FULL CYCLE ===")

            # 1) Gather raw data from sub-agents
            print("[CEOAgent] Invoking NewsProdigy...")
            news_digest = NewsProdigy().run()
            print("[CEOAgent] Invoking FinancialMarketAnalyst...")
            financial_digest = FinancialMarketAnalyst().run()
            print("[CEOAgent] Invoking EconomicAnalyst...")
            economic_digest = EconomicAnalyst().run()
            print("[CEOAgent] Invoking PoliticalAnalyst...")
            political_digest = PoliticalAnalyst().run()

            # 2) Keyword-triggered deep research
            trigger_hits = self._detect_triggers(
                news_digest, financial_digest, economic_digest, political_digest
            )
            deep_research: Dict[str, List[Dict[str, Any]]] = {}
            if trigger_hits:
                print(f"[CEOAgent] Triggers detected: {trigger_hits}")
                for keyword in trigger_hits:
                    try:
                        deep_research[keyword] = duckduckgo_search(
                            f"latest {keyword} financial markets", max_results=3
                        )
                    except Exception as e:
                        print(f"[CEOAgent] Deep research failed for '{keyword}': {e}")
                    time.sleep(0.5)

            # 3) Qualitative synthesis
            analysis = self._analyze(
                news_digest, financial_digest, economic_digest, political_digest, deep_research
            )
            print(f"[CEOAgent] Analysis complete: bias={analysis['market_bias']} risk={analysis['risk_level']} confidence={analysis['confidence']:.0f}%")

            # 4) Decision
            decision = self._decide(analysis)
            print(f"[CEOAgent] Decision: {decision['recommendation']} — {decision['summary']}")

            # 5) Trade execution (paper only)
            executed_trades: List[Dict[str, Any]] = []
            if self.enable_trade_execution and decision["recommendation"] in ("trade_freely", "reduce_size"):
                # Only enter trades when bias is clear
                if decision["market_bias"] in ("bullish", "bearish"):
                    executed_trades = self._execute_paper_trades(decision, financial_digest)
                    print(f"[CEOAgent] Executed {len(executed_trades)} paper trades.")
            elif self.enable_trade_execution and decision["recommendation"] == "close_all":
                executed_trades = self._flatten_all_positions()
                print(f"[CEOAgent] Flattened {len(executed_trades)} positions.")

            # 6) Heartbeat
            heartbeat_message = self._maybe_heartbeat(decision)
            if heartbeat_message:
                print(f"[CEOAgent] Heartbeat: {heartbeat_message}")

            # 7) Store council-level report
            self._store_council_report(decision, analysis, executed_trades, heartbeat_message)
            print("[CEOAgent] === END FULL CYCLE ===")

            return {
                "market_bias": decision["market_bias"],
                "risk_level": decision["risk_level"],
                "recommendation": decision["recommendation"],
                "confidence": decision["confidence"],
                "summary": decision["summary"],
                "triggers": sorted(trigger_hits),
                "deep_research": {k: len(v) for k, v in deep_research.items()},
                "executed_trades": executed_trades,
                "heartbeat": heartbeat_message,
            }
        except Exception as e:
            print(f"[CEOAgent] RUN ERROR: {e}")
            import traceback
            traceback.print_exc()
            error_decision = {
                "market_bias": "neutral",
                "risk_level": "high",
                "recommendation": "halt_entries",
                "confidence": 30.0,
                "bias_score": 50.0,
                "summary": f"CEO cycle failed: {e}",
            }
            self._store_council_report(error_decision, {}, [], None)
            return {"error": str(e), "summary": error_decision["summary"]}

    def _detect_triggers(self, *digests: Dict[str, Any]) -> set[str]:
        """Scan all digests for CEO trigger keywords."""
        hits = set()
        text = " ".join(str(d) for d in digests).lower()
        for kw in CEO_TRIGGERS:
            if kw in text:
                hits.add(kw)
        return hits

    def _analyze(
        self,
        news: Dict[str, Any],
        financial: Dict[str, Any],
        economic: Dict[str, Any],
        political: Dict[str, Any],
        deep_research: Dict[str, List[Dict[str, Any]]],
    ) -> Dict[str, Any]:
        """Qualitative synthesis of all sub-agent digests."""

        # --- Financial bias ---
        fin_bias = "neutral"
        bullish_count = 0
        bearish_count = 0
        rsi_readings: List[float] = []
        for snap in financial.get("snapshots", []):
            ind = snap.get("indicators", {})
            price = snap.get("price", 0)
            sma = ind.get("sma")
            ema = ind.get("ema")
            rsi_val = ind.get("rsi")
            if sma and price > sma:
                bullish_count += 1
            elif sma and price < sma:
                bearish_count += 1
            if ema and price > ema:
                bullish_count += 1
            elif ema and price < ema:
                bearish_count += 1
            if rsi_val is not None:
                rsi_readings.append(rsi_val)

        if bullish_count > bearish_count + 2:
            fin_bias = "bullish"
        elif bearish_count > bullish_count + 2:
            fin_bias = "bearish"

        avg_rsi = sum(rsi_readings) / len(rsi_readings) if rsi_readings else 50
        rsi_extreme = avg_rsi < 25 or avg_rsi > 75

        # --- News sentiment (use article_summaries if available, fall back to top_headlines) ---
        news_sentiment = "neutral"
        article_summaries = news.get("article_summaries", [])
        top_headlines = news.get("top_headlines", [])
        sentiment_pool = article_summaries if article_summaries else top_headlines
        if sentiment_pool:
            scores = [h["sentiment"] if "sentiment" in h else h.get("sentiment_score", 0) for h in sentiment_pool]
            if scores:
                avg_sent = sum(scores) / len(scores)
                if avg_sent > 0.2:
                    news_sentiment = "positive"
                elif avg_sent < -0.2:
                    news_sentiment = "negative"

        # Count critical/high headlines from article_summaries for richer context
        critical_headlines = [
            h for h in article_summaries
            if h.get("severity") in ("critical", "high")
        ]

        # --- Macro regime (qualitative) ---
        eco_counts = economic.get("bucket_counts", {})
        if eco_counts.get("growth", 0) >= 5 and eco_counts.get("inflation", 0) < 3:
            macro_regime = "expansion"
        elif eco_counts.get("inflation", 0) >= 5 and eco_counts.get("growth", 0) < 3:
            macro_regime = "stagflation"
        elif eco_counts.get("recession", 0) >= 3:
            macro_regime = "recession"
        elif eco_counts.get("rates", 0) > 3 and eco_counts.get("growth", 0) < 3:
            macro_regime = "slowdown"
        else:
            macro_regime = "recovery"

        # --- Political risk (qualitative) ---
        pol_counts = political.get("bucket_counts", {})
        raw_risk = (
            pol_counts.get("war", 0) * 30
            + pol_counts.get("crisis", 0) * 20
            + pol_counts.get("sanction", 0) * 15
            + pol_counts.get("election", 0) * 10
            + pol_counts.get("policy", 0) * 5
        )
        risk_score = min(100, raw_risk)
        if risk_score >= 70:
            risk_level = "critical"
        elif risk_score >= 50:
            risk_level = "high"
        elif risk_score >= 25:
            risk_level = "medium"
        else:
            risk_level = "low"

        # --- Aggregate bias ---
        score = 0
        if fin_bias == "bullish":
            score += 2
        elif fin_bias == "bearish":
            score -= 2
        if news_sentiment == "positive":
            score += 1
        elif news_sentiment == "negative":
            score -= 1
        if macro_regime in ("expansion", "recovery"):
            score += 1
        elif macro_regime in ("recession", "stagflation"):
            score -= 2

        if score > 1.5:
            market_bias = "bullish"
        elif score < -1.5:
            market_bias = "bearish"
        else:
            market_bias = "neutral"

        # Risk can override directional bias
        if risk_level == "critical":
            recommendation = "close_all"
        elif risk_level == "high" or market_bias == "bearish":
            recommendation = "halt_entries"
        elif risk_level == "medium" or market_bias == "neutral":
            recommendation = "reduce_size"
        else:
            recommendation = "trade_freely"

        # If RSI is extreme, tighten recommendation
        if rsi_extreme and recommendation == "trade_freely":
            recommendation = "reduce_size"

        confidence = min(100, max(30, 50 + abs(score) * 15 - risk_score * 0.3))
        if deep_research:
            confidence = min(100, confidence + 5)  # Slight boost if we did extra research

        bias_score = 50
        if market_bias == "bullish":
            bias_score = 70
        elif market_bias == "bearish":
            bias_score = 30

        summary = (
            f"CEO decision: {recommendation.replace('_', ' ').upper()}. "
            f"Bias: {market_bias} (score {score:.1f}). Risk: {risk_level.upper()} ({risk_score}/100). "
            f"Regime: {macro_regime}. Confidence: {confidence:.0f}%."
        )

        return {
            "financial_bias": fin_bias,
            "news_sentiment": news_sentiment,
            "macro_regime": macro_regime,
            "risk_score": risk_score,
            "risk_level": risk_level,
            "market_bias": market_bias,
            "recommendation": recommendation,
            "confidence": round(confidence, 1),
            "bias_score": bias_score,
            "summary": summary,
            "avg_rsi": round(avg_rsi, 1) if rsi_readings else None,
            "deep_research_topics": list(deep_research.keys()),
            "article_summaries": article_summaries[:10] if article_summaries else [],
        }

    def _decide(self, analysis: Dict[str, Any]) -> Dict[str, Any]:
        """Package the final decision."""
        return {
            "market_bias": analysis["market_bias"],
            "risk_level": analysis["risk_level"],
            "recommendation": analysis["recommendation"],
            "confidence": analysis["confidence"],
            "bias_score": analysis["bias_score"],
            "summary": analysis["summary"],
        }

    def _execute_paper_trades(
        self, decision: Dict[str, Any], financial_digest: Dict[str, Any]
    ) -> List[Dict[str, Any]]:
        """Create paper trades based on CEO directional bias."""
        executed = []
        db = SessionLocal()
        try:
            direction = "long" if decision["market_bias"] == "bullish" else "short"
            for snap in financial_digest.get("snapshots", [])[:3]:  # Top 3 assets
                asset_id = snap.get("asset_id")
                symbol = snap.get("symbol")
                price = snap.get("price")
                if not all([asset_id, symbol, price]):
                    continue
                # Skip if RSI is extreme (avoid entries into overbought/oversold)
                rsi = snap.get("indicators", {}).get("rsi")
                if rsi is not None:
                    if direction == "long" and rsi > 75:
                        continue
                    if direction == "short" and rsi < 25:
                        continue

                size = 1.0  # Simplified sizing; could be dynamic
                trade = models.Trade(
                    asset_id=asset_id,
                    direction=direction,
                    order_type=models.OrderType.MARKET,
                    entry_time=dt.datetime.utcnow(),
                    entry_price=price,
                    size=size,
                    status=models.TradeStatus.OPEN,
                    is_paper=True,
                    notes=f"CEO auto-entry: {decision['summary']}",
                    tags=["ceo_auto", decision["market_bias"], decision["risk_level"]],
                )
                db.add(trade)
                executed.append({
                    "asset_id": asset_id,
                    "symbol": symbol,
                    "direction": direction,
                    "size": size,
                    "entry_price": price,
                })
            db.commit()
            if executed:
                print(f"[CEOAgent] Executed {len(executed)} paper trades.")
        except Exception as e:
            print(f"[CEOAgent] Trade execution error: {e}")
        finally:
            db.close()
        return executed

    def _flatten_all_positions(self) -> List[Dict[str, Any]]:
        """Close all open paper trades."""
        executed = []
        db = SessionLocal()
        try:
            open_trades = (
                db.query(models.Trade)
                .filter(
                    models.Trade.status == models.TradeStatus.OPEN,
                    models.Trade.is_paper == True,
                )
                .all()
            )
            for trade in open_trades:
                # Use last known close price as exit proxy
                trade.status = models.TradeStatus.CLOSED
                trade.exit_time = dt.datetime.utcnow()
                # P&L calculation would need live price; leave as None for now
                trade.notes = (trade.notes or "") + " | CEO close-all flatten."
                executed.append({
                    "trade_id": trade.id,
                    "asset_id": trade.asset_id,
                    "direction": trade.direction.value,
                    "size": trade.size,
                })
            db.commit()
            if executed:
                print(f"[CEOAgent] Flattened {len(executed)} open paper trades.")
        except Exception as e:
            print(f"[CEOAgent] Flatten error: {e}")
        finally:
            db.close()
        return executed

    def _maybe_heartbeat(self, decision: Dict[str, Any]) -> Optional[str]:
        """Paperclip-style heartbeat every N hours."""
        now = dt.datetime.utcnow()
        if self._last_heartbeat and (now - self._last_heartbeat) < dt.timedelta(
            hours=self.heartbeat_hours
        ):
            return None

        self._last_heartbeat = now
        bias = decision["market_bias"]
        risk = decision["risk_level"]
        rec = decision["recommendation"]

        if risk == "critical":
            msg = (
                f"Hey — just checking in. The market looks rough right now ({risk.upper()} risk). "
                f"I've gone ahead and closed open positions. Stay safe out there."
            )
        elif risk == "high":
            msg = (
                f"Heads up — risk is elevated ({risk.upper()}). "
                f"I'm holding off on new entries until things calm down. "
                f"Current bias: {bias.upper()}."
            )
        elif rec == "trade_freely":
            msg = (
                f"All clear! Risk is low and bias is {bias.upper()}. "
                f"Markets look healthy — trading as usual."
            )
        else:
            msg = (
                f"Status update: bias is {bias.upper()}, risk is {risk.upper()}. "
                f"Recommendation: {rec.replace('_', ' ').upper()}. "
                f"Nothing urgent, just keeping you in the loop."
            )

        return msg

    def _store_council_report(
        self,
        decision: Dict[str, Any],
        analysis: Dict[str, Any],
        trades: List[Dict[str, Any]],
        heartbeat: Optional[str],
    ):
        db = SessionLocal()
        try:
            report = models.AgentReport(
                agent_type="ceo_agent",
                summary=decision["summary"],
                bias_score=decision["bias_score"],
                confidence=decision["confidence"],
                raw_data_json=json_safe({
                    "decision": decision["recommendation"],
                    "risk_level": decision["risk_level"],
                    "market_bias": decision["market_bias"],
                    "analysis": analysis,
                    "executed_trades": trades,
                    "heartbeat": heartbeat,
                    "article_summaries": analysis.get("article_summaries", []),
                }),
            )
            db.add(report)

            sig = models.AgentSignal(
                agent_type="ceo_agent",
                symbol="GLOBAL",
                signal=decision["market_bias"],
                strength=round(decision["confidence"] / 100, 2),
                expires_at=dt.datetime.utcnow() + dt.timedelta(hours=1),
            )
            db.add(sig)
            db.commit()
        except Exception as e:
            print(f"[CEOAgent] DB store error: {e}")
        finally:
            db.close()
