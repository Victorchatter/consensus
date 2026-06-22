"""Configurable media source list for NewsProdigy.

Feeds are persisted to a JSON file so the user can add/remove sources
without changing code.
"""
from __future__ import annotations

import json
from pathlib import Path
from typing import List

ROOT = Path(__file__).resolve().parents[3]  # backend/
DATA_DIR = ROOT / "data"
DATA_DIR.mkdir(exist_ok=True)
FEEDS_FILE = DATA_DIR / "media_sources.json"

DEFAULT_FEEDS = [
    "https://feeds.bbci.co.uk/news/business/rss.xml",
    "https://feeds.reuters.com/reuters/businessnews",
    "https://feeds.a.dj.com/rss/RSSMarketsMain.xml",
    "https://feeds.finance.yahoo.com/rss/2.0/headline?s=%5EGSPC,%5EDJI,%5EIXIC",
    "https://www.cnbc.com/id/100003114/device/rss/rss.html",
    "https://feeds.content.dowjones.io/public/rss/mw_topstories",
    "https://www.economist.com/finance-and-economics/rss.xml",
    "https://rss.cnn.com/rss/money_topstories.rss",
    "https://www.ft.com/?format=rss",
]


def _ensure_file():
    if not FEEDS_FILE.exists():
        FEEDS_FILE.write_text(json.dumps(DEFAULT_FEEDS, indent=2), encoding="utf-8")


def get_feeds() -> List[str]:
    _ensure_file()
    try:
        data = json.loads(FEEDS_FILE.read_text(encoding="utf-8"))
        if isinstance(data, list) and len(data) > 0:
            return data
    except Exception:
        pass
    return DEFAULT_FEEDS.copy()


def add_feed(url: str) -> List[str]:
    feeds = get_feeds()
    url = url.strip()
    if url and url not in feeds:
        feeds.append(url)
        FEEDS_FILE.write_text(json.dumps(feeds, indent=2), encoding="utf-8")
    return feeds


def remove_feed(url: str) -> List[str]:
    feeds = get_feeds()
    if url in feeds:
        feeds.remove(url)
        FEEDS_FILE.write_text(json.dumps(feeds, indent=2), encoding="utf-8")
    return feeds
