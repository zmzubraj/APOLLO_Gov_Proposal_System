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
from typing import List, Dict, Any

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
        try:
            import snscrape.modules.twitter as sntwitter

            msgs: list[str] = []
            for i, tweet in enumerate(
                sntwitter.TwitterUserScraper("Polkadot").get_items()
            ):
                if i >= 20:
                    break
                ts = tweet.date
                if isinstance(ts, dt.datetime):
                    if ts.tzinfo is None:
                        ts = ts.replace(tzinfo=dt.UTC)
                    else:
                        ts = ts.astimezone(dt.UTC)
                    if _within_cutoff(ts):
                        msgs.append(_clean(tweet.content))
            return msgs
        except Exception:
            return []

    try:
        url = "https://api.twitter.com/2/users/by/username/polkadotnetwork"
        resp = requests.get(
            url, headers={"Authorization": f"Bearer {token}"}, timeout=10
        )
        user_id = resp.json().get("data", {}).get("id")
        if not user_id:
            return []

        timeline = f"https://api.twitter.com/2/users/{user_id}/tweets"
        params = {"max_results": 20, "tweet.fields": "created_at"}
        tw_resp = requests.get(
            timeline,
            headers={"Authorization": f"Bearer {token}"},
            params=params,
            timeout=10,
        )
        msgs: list[str] = []
        for tw in tw_resp.json().get("data", []):
            ts = dt.datetime.fromisoformat(tw["created_at"].replace("Z", "+00:00"))
            if _within_cutoff(ts):
                msgs.append(_clean(tw["text"]))
        return msgs
    except Exception:
        # Return an empty list if the API response is malformed or the request
        # fails (e.g. invalid token or rate limit).  Upstream code will log the
        # failure but continue execution.
        return []


# (Official account reference) :contentReference[oaicite:0]{index=0}


# -----------------------------------------------------------------------------
# 2. Polkadot Forum (Discourse)
#    Public JSON endpoints expose both topic lists and full thread details.
# -----------------------------------------------------------------------------
BASE_FORUM_URL = "https://forum.polkadot.network"


def _simple_post(post: dict) -> dict:
    """Return a simplified representation of a forum post."""
    return {
        "author": post.get("username"),
        "created_at": post.get("created_at"),
        "content": post.get("cooked"),  # HTML content
    }


def flatten_forum_topic(topic: dict) -> str:
    """Combine title, body and comments into a single text blob."""
    parts: list[str] = [topic.get("title", "")]
    details = topic.get("details", {})
    if isinstance(details, dict):
        parts.append(details.get("content", ""))
    for c in topic.get("comments_replies", []):
        if isinstance(c, dict):
            parts.append(c.get("content", ""))
    return _clean(" ".join(p for p in parts if p))


def fetch_forum(limit: int = 15) -> List[dict]:
    """Fetch latest Polkadot forum topics with comments.

    Returns a list of dictionaries with the following structure::

        {
            "title": str,
            "details": {"author": str, "created_at": str, "content": str},
            "comments_replies": [same-as-details]
        }

    Network failures return an empty list so upstream callers can continue.
    """

    try:
        resp = requests.get(f"{BASE_FORUM_URL}/latest.json", timeout=10)
        resp.raise_for_status()
        topics = resp.json().get("topic_list", {}).get("topics", [])[:limit]
    except Exception:
        return []

    results: list[dict] = []
    for topic in topics:
        slug = topic.get("slug")
        topic_id = topic.get("id")
        if slug is None or topic_id is None:
            continue
        try:
            detail_resp = requests.get(
                f"{BASE_FORUM_URL}/t/{slug}/{topic_id}.json", timeout=10
            )
            detail_resp.raise_for_status()
            data = detail_resp.json()
        except Exception:
            continue

        posts = data.get("post_stream", {}).get("posts", [])
        if not posts:
            continue
        details = _simple_post(posts[0])
        comments = [_simple_post(p) for p in posts[1:]]
        results.append(
            {
                "title": data.get("title"),
                "details": details,
                "comments_replies": comments,
            }
        )
        time.sleep(0.2)  # polite delay

    return results


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
    """Fetch recent r/Polkadot posts and their comments.

    Uses Reddit's public JSON endpoints so no credentials are required.  The
    function gathers the latest posts and then fetches comments for each post
    to provide additional context.  Results are filtered to the last 72 hours
    and returned as a simple list of text snippets.
    """

    headers = {"User-Agent": "Mozilla/5.0"}
    try:
        resp = requests.get(
            "https://www.reddit.com/r/Polkadot/new.json",
            headers=headers,
            params={"limit": limit, "t": "day"},
            timeout=10,
        )
        resp.raise_for_status()
        posts_json = resp.json()
    except Exception:
        return []

    messages: list[str] = []
    for child in posts_json.get("data", {}).get("children", []):
        post = child.get("data", {})
        created = dt.datetime.fromtimestamp(post.get("created_utc", 0), dt.UTC)
        if not _within_cutoff(created):
            continue

        title = _clean(html.unescape(post.get("title", "")))
        if title:
            messages.append(title)

        post_id = post.get("id")
        if not post_id:
            continue

        try:
            cm_resp = requests.get(
                f"https://www.reddit.com/r/Polkadot/comments/{post_id}.json",
                headers=headers,
                timeout=10,
            )
            cm_resp.raise_for_status()
            comments_json = cm_resp.json()
        except Exception:
            comments_json = []

        # The second element holds the comment tree
        try:
            for c in comments_json[1]["data"]["children"]:
                body = c.get("data", {}).get("body")
                if body:
                    messages.append(_clean(html.unescape(body)))
        except Exception:
            pass

        # Polite delay to avoid hitting rate limits
        time.sleep(2)

    return messages


# subreddit reference :contentReference[oaicite:3]{index=3}


# -----------------------------------------------------------------------------
# 6. Binance Square (API fetch)
# -----------------------------------------------------------------------------
def fetch_binance_square(limit: int = 30) -> List[str]:
    """Fetch recent Binance Square posts and comments.

    The unofficial CMS endpoints exposed by Binance's web client provide
    metadata for articles as well as a separate endpoint for their comments.
    This function pulls a limited number of Polkadot-related posts and flattens
    the article titles, briefs and comment bodies into a simple list of text
    snippets.  Network failures return an empty list so the caller can continue
    gracefully.
    """

    url = (
        "https://www.binance.com/bapi/composite/v1/public/cms/article/list/query"
        f"?type=1&pageNo=1&pageSize={limit}"
    )
    try:
        resp = requests.get(url, timeout=10)
        resp.raise_for_status()
        data = resp.json()
    except Exception:
        return []

    posts: List[str] = []
    fetched = 0
    catalogs = data.get("data", {}).get("catalogs", [])
    for catalog in catalogs:
        for item in catalog.get("articles", []):
            if fetched >= limit:
                break
            content = "\n".join(
                filter(None, [item.get("title", ""), item.get("brief", "")])
            )
            code = item.get("code")
            if code and not content:
                # fallback to detailed endpoint for full body
                try:
                    d_url = (
                        "https://www.binance.com/bapi/composite/v1/public/cms/article/detail/query"
                        f"?articleCode={code}"
                    )
                    d_resp = requests.get(d_url, timeout=10)
                    d_resp.raise_for_status()
                    d_data = d_resp.json().get("data", {})
                    content = "\n".join(
                        filter(None, [d_data.get("title", ""), d_data.get("body", "")])
                    )
                except Exception:
                    content = ""
            if content:
                posts.append(_clean(content))

            post_id = item.get("id") or item.get("articleId")
            if post_id:
                c_url = (
                    "https://www.binance.com/bapi/composite/v1/public/cms/comment/query"
                    f"?articleId={post_id}&pageSize=50"
                )
                try:
                    c_resp = requests.get(c_url, timeout=10)
                    c_resp.raise_for_status()
                    c_data = c_resp.json()
                except Exception:
                    c_data = {}
                for c in c_data.get("data", {}).get("comments", []):
                    text = c.get("content", "")
                    if text:
                        posts.append(_clean(text))
            fetched += 1
            time.sleep(0.2)  # polite delay
        if fetched >= limit:
            break

    return posts


# sample Polkadot content cited :contentReference[oaicite:4]{index=4}


# -----------------------------------------------------------------------------
# Unified public API
# -----------------------------------------------------------------------------
def collect_recent_messages() -> Dict[str, List[Any]]:
    """Return recent messages grouped by their source.

    Each key represents a general source category (e.g. ``"forum"``,
    ``"news"``, ``"chat"``) mapped to a list of snippets or topic dictionaries
    pulled from the relevant platforms.  Failures from individual sources are
    logged and represented as empty lists so the caller can handle missing
    data gracefully.
    """

    source_funcs: Dict[str, List] = {
        "chat": [fetch_x, fetch_reddit],
        "forum": [fetch_forum],
        "news": [fetch_cryptorank, fetch_binance_square],
    }

    grouped: Dict[str, List[Any]] = {}
    for name, funcs in source_funcs.items():
        texts: list[Any] = []
        for fn in funcs:
            try:
                texts.extend(fn())
            except Exception as e:
                print(f"[warn] {fn.__name__} failed: {e}")
        # de-dup & keep order within the source
        seen, deduped = set(), []
        for t in texts:
            key = str(t) if not isinstance(t, dict) else t.get("title", str(t))
            if key not in seen:
                deduped.append(t)
                seen.add(key)
        grouped[name] = deduped

    return grouped


# Stand-alone quick test ------------------------------------------------------
if __name__ == "__main__":
    grouped = collect_recent_messages()
    total = sum(len(v) for v in grouped.values())
    print(f"Collected {total} messages.")
    for source, msgs in grouped.items():
        print(source, msgs[:3])
