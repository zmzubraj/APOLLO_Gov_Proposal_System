"""Telegram connector to post proposal summaries via bot API."""
from __future__ import annotations

import os
from typing import Optional

import requests


def post_summary(
    summary: str,
    token: Optional[str] = None,
    chat_id: Optional[str] = None,
) -> bool:
    """Send ``summary`` to Telegram chat using Bot API.

    Parameters
    ----------
    summary: str
        Message content to send.
    token: Optional[str]
        Bot token. If ``None``, uses ``TELEGRAM_BOT_TOKEN`` env var.
    chat_id: Optional[str]
        Target chat ID. If ``None``, uses ``TELEGRAM_CHAT_ID`` env var.

    Returns
    -------
    bool
        ``True`` if the request was sent successfully, ``False`` otherwise.
    """
    token = token or os.getenv("TELEGRAM_BOT_TOKEN")
    chat_id = chat_id or os.getenv("TELEGRAM_CHAT_ID")
    if not token or not chat_id:
        return False
    url = f"https://api.telegram.org/bot{token}/sendMessage"
    resp = requests.post(url, json={"chat_id": chat_id, "text": summary})
    return resp.ok
