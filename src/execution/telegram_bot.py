"""Telegram connector utilities."""
from __future__ import annotations

import os
from typing import Optional, List

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


def poll_messages(
    token: Optional[str] = None,
    chat_id: Optional[str] = None,
    limit: int = 50,
) -> List[str]:
    """Return recent text messages for ``chat_id``.

    Parameters
    ----------
    token, chat_id: Optional[str]
        Bot credentials. If omitted, environment variables
        ``TELEGRAM_BOT_TOKEN`` and ``TELEGRAM_CHAT_ID`` are used.
    limit: int
        Maximum number of updates to request.

    Returns
    -------
    list[str]
        Plain-text message bodies.
    """
    token = token or os.getenv("TELEGRAM_BOT_TOKEN")
    chat_id = chat_id or os.getenv("TELEGRAM_CHAT_ID")
    if not token:
        return []
    url = f"https://api.telegram.org/bot{token}/getUpdates"
    params = {"limit": limit}
    try:
        resp = requests.get(url, params=params, timeout=10)
        if not resp.ok:
            return []
        updates = resp.json().get("result", [])
        messages: List[str] = []
        for upd in updates:
            msg = upd.get("message") or upd.get("channel_post") or {}
            if chat_id and str(msg.get("chat", {}).get("id")) != str(chat_id):
                continue
            text = msg.get("text")
            if text:
                messages.append(text)
        return messages
    except Exception:
        return []
