"""Simple Discord connector to post proposal summaries via webhooks."""
from __future__ import annotations

import os
from typing import Optional

import requests


def post_summary(summary: str, webhook_url: Optional[str] = None) -> bool:
    """Post ``summary`` to Discord using a webhook URL.

    Parameters
    ----------
    summary: str
        The message to send.
    webhook_url: Optional[str]
        Explicit webhook URL. If ``None``, uses ``DISCORD_WEBHOOK_URL`` env var.

    Returns
    -------
    bool
        ``True`` if the request was sent successfully, ``False`` otherwise.
    """
    url = webhook_url or os.getenv("DISCORD_WEBHOOK_URL")
    if not url:
        return False
    resp = requests.post(url, json={"content": summary})
    return resp.ok
