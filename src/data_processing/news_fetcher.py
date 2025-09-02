"""
news_fetcher.py
---------------
Fetch Polkadot-related headlines from multiple RSS feeds (configurable
look-back, default 3 days) and summarise them with the LLM.

# Usage:
# >>> from src.data_processing.news_fetcher import fetch_and_summarise_news
# >>> digest = fetch_and_summarise_news()
# """

from __future__ import annotations
from typing import List, Dict, Any
import os
import datetime as dt
import feedparser, requests
from bs4 import BeautifulSoup
from llm.ollama_api import generate_completion, OllamaError
from utils.helpers import extract_json_safe

# ---------------------------------------------------------------------------
RSS_FEEDS = [
    "https://cointelegraph.com/rss/tag/polkadot",
    "https://www.coindesk.com/arc/outboundfeeds/rss/?outputType=xml&search=polkadot",
    "https://polkadot.network/blog/rss.xml",
]
LOOKBACK_DAYS = int(os.getenv("NEWS_LOOKBACK_DAYS", 30))
MAX_ARTICLES = 50

SYSTEM_PROMPT = """
Return ONLY minified JSON with two keys:
{"digest":["bullet1","bullet2","bullet3"],"risks":"one sentence"}
No markdown, no back-ticks, ≤150 tokens total.
""".strip()
# ---------------------------------------------------------------------------


def _parse_entry(entry) -> Dict[str, Any]:
    return {
        "title": entry.title,
        "summary": BeautifulSoup(getattr(entry, "summary", ""), "html.parser").get_text()[:280],
        "published": dt.datetime(*entry.published_parsed[:6], tzinfo=dt.UTC)
        if getattr(entry, "published_parsed", None)
        else dt.datetime.now(dt.UTC),
    }


def _collect_recent_items(lookback_days: int = LOOKBACK_DAYS) -> List[Dict[str, Any]]:
    cutoff = dt.datetime.now(dt.UTC) - dt.timedelta(days=lookback_days)
    items: list[dict] = []
    for url in RSS_FEEDS:
        for e in feedparser.parse(url).entries:
            it = _parse_entry(e)
            if it["published"] >= cutoff:
                items.append(it)
    # unique by title
    seen, uniq = set(), []
    for it in sorted(items, key=lambda x: x["published"], reverse=True):
        if it["title"] not in seen:
            uniq.append(it)
            seen.add(it["title"])
            if len(uniq) >= MAX_ARTICLES:
                break
    return uniq


def summarise_items(items: List[Dict[str, Any]], model: str | None = None) -> Dict[str, Any]:
    if not items:
        return {"digest": [], "risks": "No recent Polkadot news."}

    bullet_source = "\n\n".join(f"- {it['title']}: {it['summary']}" for it in items)

    try:
        raw = generate_completion(
            prompt=bullet_source[:8000],
            system=SYSTEM_PROMPT,
            model="gemma3:4b",
            temperature=0.2,
            max_tokens=256,
        )
    except OllamaError as err:
        # If the local Ollama server is unavailable (e.g. not installed or not
        # running) we don't want the whole pipeline to crash.  Instead return a
        # friendly message so callers can handle the absence of a summary.
        return {"digest": [], "risks": f"LLM summary failed: {err}"}

    parsed = extract_json_safe(raw)
    return parsed or {"digest": [], "risks": "LLM summary failed."}


# Public one-shot helper ------------------------------------------------------
def fetch_and_summarise_news(model: str | None = None) -> Dict[str, Any]:
    return summarise_items(_collect_recent_items(), model)


# CLI test --------------------------------------------------------------------
if __name__ == "__main__":
    news = fetch_and_summarise_news()
    print(news)

