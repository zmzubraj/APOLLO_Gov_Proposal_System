"""
news_fetcher.py
---------------
Fetch latest Polkadot-related articles via RSS and simple web search,
then summarise with the selected LLM.
"""

from __future__ import annotations
from typing import List, Dict, Any
import datetime as dt
import logging
import feedparser
from bs4 import BeautifulSoup
from llm.ollama_api import generate_completion
from analysis.sentiment_analysis import _extract_json

logger = logging.getLogger(__name__)

RSS_FEEDS = [
    "https://cointelegraph.com/rss/tag/polkadot",           # Cointelegraph Polkadot
    "https://www.coindesk.com/arc/outboundfeeds/rss/?outputType=xml&search=polkadot",
]

MAX_ARTICLES = 10          # total to summarise
LOOKBACK_DAYS = 25          # only keep recent items


def _fetch_rss_items() -> List[Dict[str, Any]]:
    """Collect items from RSS feeds and filter by recency."""
    items: list[dict] = []
    cutoff = dt.datetime.now(dt.UTC) - dt.timedelta(days=LOOKBACK_DAYS)

    for url in RSS_FEEDS:
        feed = feedparser.parse(url)
        for entry in feed.entries:
            published = (
                dt.datetime(*entry.published_parsed[:6], tzinfo=dt.UTC)
                if "published_parsed" in entry
                else dt.datetime.now(dt.UTC)
            )
            if published < cutoff:
                continue
            items.append(
                {
                    "title": entry.title,
                    "link": entry.link,
                    "published": published.isoformat(),
                    "summary": BeautifulSoup(entry.summary, "html.parser").get_text()
                    if "summary" in entry
                    else "",
                }
            )

    # de-dupe & keep newest
    seen = set()
    uniq = []
    for it in sorted(items, key=lambda x: x["published"], reverse=True):
        if it["title"] not in seen:
            uniq.append(it)
            seen.add(it["title"])
        if len(uniq) >= MAX_ARTICLES:
            break
    return uniq


SYSTEM_PROMPT = """
You are a Polkadot governance analyst.
Summarise the following news items into:
  • bullet-point digest (max 5 bullets)
  • notable risks or opportunities (1-2 sentences)
Return ONLY minified JSON:
{"digest":["..."],"risks":"..."}
""".strip()


def summarise_news(items: List[Dict[str, Any]]) -> Dict[str, Any]:
    """
    Use LLM to compress the list of items into a structured summary.
    """
    if not items:
        return {"digest": [], "risks": "No recent Polkadot news in the last 3 days."}

    bullet_source = "\n\n".join(f"- {itm['title']}: {itm['summary']}" for itm in items)
    # print(bullet_source)

    raw = generate_completion(
        prompt=bullet_source[:8000],
        system=SYSTEM_PROMPT,
        temperature=0.2,
        max_tokens=512,
        model="gemma3:4b",
    )

    logger.debug("Response summary: %s", raw)

    # reuse extractor from sentiment module
    parsed = _extract_json(raw)
    if parsed is None:
        return {"digest": [], "risks": "LLM summary failed."}
    return parsed


# ────────────────────────────────────────────────────────────────────────────
# Stand-alone test
# ────────────────────────────────────────────────────────────────────────────
if __name__ == "__main__":
    articles = _fetch_rss_items()
    print(f"Fetched {len(articles)} news items.")
    summary = summarise_news(articles)
    print("Final Outcome: \n", summary)

