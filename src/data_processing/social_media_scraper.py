"""
social_media_scraper.py
-----------------------
Light-weight collectors for Polkadot chatter across six platforms.

Only *public* or *official* APIs / JSON feeds are used.
If API tokens are not provided in the environment, the function falls
back to an empty list for that source so the pipeline can still run.
"""

from __future__ import annotations

import datetime as dt
import html
import os
import re
import time
from typing import List, Dict

import requests
from bs4 import BeautifulSoup

# -----------------------------------------------------------------------------
# Utility
# -----------------------------------------------------------------------------
UTC_CUTOFF = dt.datetime.now(dt.UTC) - dt.timedelta(days=3)  # last 72 h


def _within_cutoff(ts: dt.datetime) -> bool:
    return ts >= UTC_CUTOFF


def _clean(text: str) -> str:
    """Collapse whitespace + strip."""
    return re.sub(r"\s+", " ", text).strip()


# -----------------------------------------------------------------------------
# 1. X / Twitter (@PolkadotNetwork)
#    Requires a bearer token (X API v2) – set TWITTER_BEARER env var
# -----------------------------------------------------------------------------
def fetch_x() -> List[str]:
    token = os.getenv("TWITTER_BEARER")
    if not token:
        return []

    url = "https://api.twitter.com/2/users/by/username/polkadotnetwork"
    user_id = requests.get(url, headers={"Authorization": f"Bearer {token}"}).json()["data"]["id"]

    timeline = f"https://api.twitter.com/2/users/{user_id}/tweets"
    params = {"max_results": 20, "tweet.fields": "created_at"}
    resp = requests.get(timeline, headers={"Authorization": f"Bearer {token}"}, params=params).json()
    msgs: list[str] = []
    for tw in resp.get("data", []):
        ts = dt.datetime.fromisoformat(tw["created_at"].replace("Z", "+00:00"))
        if _within_cutoff(ts):
            msgs.append(_clean(tw["text"]))
    return msgs


# (Official account reference) :contentReference[oaicite:0]{index=0}


# -----------------------------------------------------------------------------
# 2. Polkadot Forum (Discourse)
#    Public JSON endpoint: https://forum.polkadot.network/latest.json
# -----------------------------------------------------------------------------
def fetch_forum() -> List[str]:
    r = requests.get("https://forum.polkadot.network/latest.json", timeout=10)
    latest = r.json().get("topic_list", {}).get("topics", [])
    msgs: list[str] = []
    for t in latest[:15]:
        created = (
            dt.datetime.fromtimestamp(t["created_at"] // 1000, dt.UTC)
            if isinstance(t["created_at"], int)
            else dt.datetime.strptime(t["created_at"][:19], "%Y-%m-%dT%H:%M:%S").replace(tzinfo=dt.UTC)
        )
        if _within_cutoff(created):
            msgs.append(_clean(t["title"]))
    return msgs


# discourse JSON endpoint confirmed :contentReference[oaicite:1]{index=1}


# -----------------------------------------------------------------------------
# 3. CryptoRank (News page)
#    Simple HTML scrape
# -----------------------------------------------------------------------------
def fetch_cryptorank() -> List[str]:
    url = "https://cryptorank.io/news/polkadot"
    try:
        soup = BeautifulSoup(requests.get(url, timeout=10).text, "html.parser")
    except Exception:
        return []
    items = soup.select("div.news-item__content")[:15]
    return [_clean(i.get_text(" ", strip=True)) for i in items]


# -----------------------------------------------------------------------------
# 4. Telegram (PolkadotAnnouncements channel)
#    Requires TELEGRAM_API_ID & TELEGRAM_API_HASH (Telethon library)
# -----------------------------------------------------------------------------
# def fetch_telegram() -> List[str]:
#     from telethon import TelegramClient
#
#     api_id = int(os.getenv("TELEGRAM_API_ID"))
#     api_hash = os.getenv("TELEGRAM_API_HASH")
#     if not api_id or not api_hash:
#         return []
#
#     client = TelegramClient("pd_temp", api_id, api_hash)
#     msgs: list[str] = []
#
#     async def _pull():
#         async for m in client.iter_messages("PolkadotAnnouncements", limit=30):
#             if m.date and _within_cutoff(m.date):
#                 if m.text:
#                     msgs.append(_clean(m.text))
#
#     with client:
#         client.loop.run_until_complete(_pull())
#     return msgs


# public channel reference :contentReference[oaicite:2]{index=2}


# -----------------------------------------------------------------------------
# 5. Reddit r/Polkadot
#    Uses PRAW – requires REDDIT_CLIENT_ID, REDDIT_SECRET, REDDIT_USERAGENT
# -----------------------------------------------------------------------------
def fetch_reddit(limit: int = 20) -> List[str]:
    """
    Pull recent posts + top comments from r/Polkadot via the public JSON
    endpoints.  No credentials required.  Limited to ~100 requests / 10 min
    per Reddit's unauthenticated rate-limit.:contentReference[oaicite:0]{index=0}
    """
    base = "https://www.reddit.com"
    headers = {"User-Agent": "pd-gov-bot/0.1 (public data)"}
    url = f"{base}/r/Polkadot/new.json?limit={limit}"
    try:
        data = requests.get(url, headers=headers, timeout=10).json()
    except Exception:
        return []

    msgs: list[str] = []
    for post in data.get("data", {}).get("children", []):
        p = post["data"]
        created = dt.datetime.fromtimestamp(p["created_utc"], dt.UTC)
        if not _within_cutoff(created):
            continue
        title = html.unescape(p["title"])
        msgs.append(_clean(title))

        # Pull top 3 top-level comments for extra sentiment signal
        permalink = p["permalink"]
        try:
            thread = requests.get(f"{base}{permalink}.json?limit=3",
                                  headers=headers, timeout=10).json()
            if len(thread) > 1:
                for c in thread[1]["data"]["children"][:3]:
                    body = c["data"].get("body")
                    if body:
                        msgs.append(_clean(html.unescape(body)))
            # be polite to Reddit
            time.sleep(1)
        except Exception:
            pass
    return msgs


# subreddit reference :contentReference[oaicite:3]{index=3}


# -----------------------------------------------------------------------------
# 6. Binance Square (web scrape)
# -----------------------------------------------------------------------------
def fetch_binance_square() -> List[str]:
    url = "https://www.binance.com/en/square/post"
    soup = BeautifulSoup(requests.get(url, timeout=10).text, "html.parser")
    cards = soup.select("div.css-1ej4hfo")[:15]  # class may change
    return [_clean(c.get_text(" ", strip=True)) for c in cards]


# sample Polkadot content cited :contentReference[oaicite:4]{index=4}


# -----------------------------------------------------------------------------
# Unified public API
# -----------------------------------------------------------------------------
def collect_recent_messages() -> Dict[str, List[str]]:
    """Return recent messages grouped by their source.

    Each key represents a general source category (e.g. ``"forum"``,
    ``"news"``, ``"chat"``) mapped to a list of text snippets pulled from the
    relevant platforms.  Failures from individual sources are logged and
    represented as empty lists so the caller can handle missing data
    gracefully.
    """

    source_funcs: Dict[str, List] = {
        "chat": [fetch_x, fetch_reddit],
        "forum": [fetch_forum],
        "news": [fetch_cryptorank, fetch_binance_square],
    }

    grouped: Dict[str, List[str]] = {}
    for name, funcs in source_funcs.items():
        texts: list[str] = []
        for fn in funcs:
            try:
                texts.extend(fn())
            except Exception as e:
                print(f"[warn] {fn.__name__} failed: {e}")
        # de-dup & keep order within the source
        seen, deduped = set(), []
        for t in texts:
            if t not in seen:
                deduped.append(t)
                seen.add(t)
        grouped[name] = deduped

    return grouped


# Stand-alone quick test ------------------------------------------------------
if __name__ == "__main__":
    data = collect_recent_messages()
    print(f"Collected {len(data)} messages.")
    print(data[:10])
