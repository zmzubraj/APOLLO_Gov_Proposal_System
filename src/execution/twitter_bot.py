"""Twitter connector utilities using API v2."""
from __future__ import annotations

import os
from typing import Optional, List

import requests


def post_summary(summary: str, bearer_token: Optional[str] = None) -> bool:
    """Post ``summary`` to Twitter using API v2 ``/tweets`` endpoint.

    Parameters
    ----------
    summary: str
        Tweet text.
    bearer_token: Optional[str]
        API bearer token. If ``None``, uses ``TWITTER_BEARER`` env var.

    Returns
    -------
    bool
        ``True`` if the request was sent successfully, ``False`` otherwise.
    """
    token = bearer_token or os.getenv("TWITTER_BEARER")
    if not token:
        return False
    url = "https://api.twitter.com/2/tweets"
    headers = {"Authorization": f"Bearer {token}"}
    resp = requests.post(url, json={"text": summary}, headers=headers)
    return resp.ok


def poll_messages(
    query: str,
    bearer_token: Optional[str] = None,
    max_results: int = 10,
) -> List[str]:
    """Return recent tweets matching ``query``.

    Parameters
    ----------
    query: str
        Search query string, e.g. a hashtag or keywords.
    bearer_token: Optional[str]
        API bearer token. If ``None``, uses ``TWITTER_BEARER`` env var.
    max_results: int
        Max number of tweets to return (up to 100 per API docs).

    Returns
    -------
    list[str]
        Tweet text contents.
    """
    token = bearer_token or os.getenv("TWITTER_BEARER")
    if not token:
        return []
    url = "https://api.twitter.com/2/tweets/search/recent"
    headers = {"Authorization": f"Bearer {token}"}
    params = {"query": query, "max_results": max_results}
    try:
        resp = requests.get(url, headers=headers, params=params, timeout=10)
        if not resp.ok:
            return []
        data = resp.json().get("data", [])
        return [t.get("text", "") for t in data]
    except Exception:
        return []
