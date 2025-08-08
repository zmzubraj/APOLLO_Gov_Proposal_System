"""Simple Discord connector utilities."""
from __future__ import annotations

import os
from typing import Optional, List

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


def poll_messages(
    channel_id: str,
    token: Optional[str] = None,
    limit: int = 50,
) -> List[str]:
    """Return recent message contents from a Discord channel.

    Parameters
    ----------
    channel_id: str
        Identifier of the Discord channel to poll.
    token: Optional[str]
        Bot token. If ``None``, uses ``DISCORD_BOT_TOKEN`` env var.
    limit: int
        Maximum number of messages to fetch.

    Returns
    -------
    list[str]
        Plain-text contents of retrieved messages.
    """
    token = token or os.getenv("DISCORD_BOT_TOKEN")
    if not token:
        return []
    url = f"https://discord.com/api/v10/channels/{channel_id}/messages"
    headers = {"Authorization": f"Bot {token}"}
    params = {"limit": limit}
    try:
        resp = requests.get(url, headers=headers, params=params, timeout=10)
        if not resp.ok:
            return []
        return [m.get("content", "") for m in resp.json()]
    except Exception:
        return []
