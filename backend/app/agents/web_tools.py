"""Lightweight web search + fetch utilities for agents.

Zero-dependency internet access using only built-in urllib.
DuckDuckGo HTML search endpoint (no API key required).
"""
from __future__ import annotations

import re
import ssl
import time
import urllib.request
import urllib.parse
import xml.etree.ElementTree as ET
from typing import List, Dict, Any, Optional

try:
    import certifi
    _SSL_CTX = ssl.create_default_context(cafile=certifi.where())
except Exception:
    _SSL_CTX = ssl.create_default_context()


USER_AGENT = (
    "Mozilla/5.0 (Windows NT 10.0; Win64; x64) "
    "AppleWebKit/537.36 (KHTML, like Gecko) Chrome/125.0.0.0 Safari/537.36"
)

_DEFAULT_HEADERS = {
    "User-Agent": USER_AGENT,
    "Accept": "text/html,application/xhtml+xml,application/xml;q=0.9,*/*;q=0.8",
    "Accept-Language": "en-US,en;q=0.5",
    "Accept-Encoding": "identity",
    "Connection": "keep-alive",
    "Upgrade-Insecure-Requests": "1",
}

# Simple circuit-breaker for DDG to avoid spamming logs on persistent failures
_DDG_CB = {"failures": 0, "last_fail": 0.0, "cooldown_sec": 3600}

# In-memory fetch cache: url -> (timestamp, result)
_FETCH_CACHE: Dict[str, tuple] = {}
_CACHE_TTL_SEC = 60  # default 1 minute


def _ddg_circuit_open() -> bool:
    """Return True if we should skip DDG because of too many recent failures."""
    if _DDG_CB["failures"] >= 3:
        if time.time() - _DDG_CB["last_fail"] < _DDG_CB["cooldown_sec"]:
            return True
        # Reset after cooldown
        _DDG_CB["failures"] = 0
    return False


def _ddg_record_fail():
    _DDG_CB["failures"] += 1
    _DDG_CB["last_fail"] = time.time()


def _ddg_record_ok():
    _DDG_CB["failures"] = max(0, _DDG_CB["failures"] - 1)


def _build_request(url: str) -> urllib.request.Request:
    req = urllib.request.Request(url)
    for k, v in _DEFAULT_HEADERS.items():
        req.add_header(k, v)
    return req


def fetch_html(url: str, timeout: int = 20) -> str:
    """Fetch raw HTML from a URL."""
    req = _build_request(url)
    with urllib.request.urlopen(req, timeout=timeout, context=_SSL_CTX) as resp:
        return resp.read().decode("utf-8", errors="replace")


def cached_fetch(url: str, timeout: int = 20, ttl_sec: int = _CACHE_TTL_SEC) -> str:
    """Fetch with simple in-memory caching to avoid hammering the same URL."""
    now = time.time()
    cached = _FETCH_CACHE.get(url)
    if cached:
        ts, data = cached
        if now - ts < ttl_sec:
            return data
    data = fetch_html(url, timeout=timeout)
    _FETCH_CACHE[url] = (now, data)
    return data


def parse_rss_feed(raw_xml: str, source_url: str) -> List[Dict[str, Any]]:
    """Parse RSS/Atom XML and return a list of article dicts.

    Handles both RSS <item> and Atom <entry> formats.
    Defensively strips DOCTYPE to mitigate XXE / billion-laughs.
    """
    # Strip DOCTYPE to avoid parser issues with external entities
    text = re.sub(r"<!DOCTYPE\s+[^>]*\[[^\]]*\]>", "", raw_xml, flags=re.DOTALL)
    text = re.sub(r"<!DOCTYPE\s+[^>]*>", "", text, flags=re.DOTALL)
    # Remove XML declaration if present
    text = re.sub(r"<\?xml[^\?]*\?>", "", text)

    try:
        # Use a parser with entity expansion limits for safety
        parser = ET.XMLParser()
        # Python 3.14+ may not have these attributes, so guard with hasattr
        if hasattr(parser, "entity"):
            parser.entity = {}
        root = ET.fromstring(text.encode("utf-8"), parser=parser)
    except ET.ParseError as e:
        print(f"[RSSParser] XML parse error for {source_url}: {e}")
        return []

    items: List[Dict[str, Any]] = []

    # Detect Atom vs RSS by root tag
    tag = root.tag.split("}")[-1] if "}" in root.tag else root.tag
    if tag == "feed":
        # Atom format
        for entry in root.iter("{http://www.w3.org/2005/Atom}entry"):
            title = entry.findtext("{http://www.w3.org/2005/Atom}title", default="")
            link_elem = entry.find("{http://www.w3.org/2005/Atom}link")
            link = link_elem.get("href", "") if link_elem is not None else ""
            published = entry.findtext("{http://www.w3.org/2005/Atom}published", default="")
            summary = entry.findtext("{http://www.w3.org/2005/Atom}summary", default="")
            items.append({
                "title": (title or "").strip(),
                "description": (summary or "").strip(),
                "published": published,
                "url": link,
                "source": source_url,
            })
    else:
        # RSS format (root is rss/channel or rdf/RDF)
        for item in root.iter("item"):
            title = item.findtext("title", default="")
            desc = item.findtext("description", default="")
            pub = item.findtext("pubDate", default="")
            link = item.findtext("link", default="")
            # Some feeds use guid as URL fallback
            if not link:
                guid = item.findtext("guid", default="")
                if guid and guid.startswith("http"):
                    link = guid
            items.append({
                "title": (title or "").strip(),
                "description": (desc or "").strip(),
                "published": pub,
                "url": link,
                "source": source_url,
            })

    return items


def extract_title_from_html(html: str) -> str:
    """Extract <title> tag from raw HTML as a fallback for non-RSS pages."""
    m = re.search(r"<title>(.*?)</title>", html, re.DOTALL | re.IGNORECASE)
    if m:
        return re.sub(r"<[^>]+>", "", m.group(1)).strip()
    return ""


def fetch_feed_or_scrape(url: str, timeout: int = 15) -> List[Dict[str, Any]]:
    """Fetch a URL and try RSS parsing first, then fall back to HTML title extraction."""
    try:
        raw = cached_fetch(url, timeout=timeout, ttl_sec=120)
    except Exception as e:
        print(f"[Fetch] Failed {url}: {e}")
        return []

    # Try RSS/Atom first
    items = parse_rss_feed(raw, url)
    if items:
        print(f"[Fetch] RSS OK: {url} — {len(items)} items")
        return items

    # Fallback: treat as HTML and extract a single title
    title = extract_title_from_html(raw)
    if title:
        print(f"[Fetch] HTML fallback: {url} — title='{title}'")
        return [{
            "title": title,
            "description": "",
            "published": "",
            "url": url,
            "source": url,
        }]

    print(f"[Fetch] No parseable content: {url}")
    return []


def duckduckgo_search(query: str, max_results: int = 5) -> List[Dict[str, Any]]:
    """Search DuckDuckGo HTML endpoint and return title+snippet+url results."""
    if _ddg_circuit_open():
        return []

    url = "https://html.duckduckgo.com/html/?q=" + urllib.parse.quote(query)
    html = ""

    # Try once with a longer timeout; on timeout, retry once after a short sleep
    for attempt in range(2):
        try:
            html = fetch_html(url, timeout=25)
            break
        except Exception:
            if attempt == 0:
                time.sleep(2.0)
                continue
            _ddg_record_fail()
            return []

    if not html:
        _ddg_record_fail()
        return []

    results = []
    # DuckDuckGo HTML result blocks
    for m in re.finditer(
        r'<a[^>]*class="result__a"[^>]*href="([^"]*)"[^>]*>(.*?)</a>',
        html,
        re.DOTALL | re.IGNORECASE,
    ):
        link = m.group(1)
        title = re.sub(r"<[^>]+>", "", m.group(2)).strip()
        if not title or not link:
            continue
        # DuckDuckGo redirects through their own URL
        if link.startswith("//"):
            link = "https:" + link
        elif link.startswith("/"):
            link = "https://duckduckgo.com" + link
        results.append({"title": title, "url": link})
        if len(results) >= max_results:
            break

    # Extract snippets
    snippets = re.findall(
        r'<a[^>]*class="result__snippet"[^>]*>(.*?)</a>', html, re.DOTALL | re.IGNORECASE
    )
    for i, snippet_html in enumerate(snippets):
        if i >= len(results):
            break
        snippet = re.sub(r"<[^>]+>", "", snippet_html).strip()
        results[i]["snippet"] = snippet

    _ddg_record_ok()
    return results


def search_news(query: str, max_results: int = 5) -> List[Dict[str, Any]]:
    """Search for news using DuckDuckGo."""
    return duckduckgo_search(query + " news", max_results=max_results)


def extract_text_from_html(html: str, max_chars: int = 2000) -> str:
    """Naive HTML-to-text extraction."""
    text = re.sub(r"<script[^>]*>.*?</script>", "", html, flags=re.DOTALL | re.IGNORECASE)
    text = re.sub(r"<style[^>]*>.*?</style>", "", text, flags=re.DOTALL | re.IGNORECASE)
    text = re.sub(r"<[^>]+>", " ", text)
    text = re.sub(r"\s+", " ", text).strip()
    return text[:max_chars]
