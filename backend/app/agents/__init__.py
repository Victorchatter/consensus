from __future__ import annotations

from app.agents.news_prodigy import NewsProdigy
from app.agents.financial_analyst import FinancialMarketAnalyst
from app.agents.economic_analyst import EconomicAnalyst
from app.agents.political_analyst import PoliticalAnalyst
from app.agents.ceo_agent import CEOAgent
from app.agents.scheduler import AgentScheduler

__all__ = [
    "NewsProdigy",
    "FinancialMarketAnalyst",
    "EconomicAnalyst",
    "PoliticalAnalyst",
    "CEOAgent",
    "AgentScheduler",
]
