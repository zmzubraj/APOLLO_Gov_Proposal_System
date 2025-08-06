"""Twitter connector to post proposal summaries via API v2."""
from __future__ import annotations

import os
from typing import Optional

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
