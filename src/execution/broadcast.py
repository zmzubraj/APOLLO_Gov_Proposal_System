"""Utility to broadcast proposals to community platforms."""
from __future__ import annotations

from .discord_bot import post_summary as post_discord
from .telegram_bot import post_summary as post_telegram
from .twitter_bot import post_summary as post_twitter


def broadcast_proposal(text: str) -> None:
    """Send ``text`` to any configured community platforms."""
    sent = []
    if post_discord(text):
        sent.append("Discord")
    if post_telegram(text):
        sent.append("Telegram")
    if post_twitter(text):
        sent.append("Twitter")
    if sent:
        print("📢 Broadcasted proposal to " + ", ".join(sent))
    else:
        print("⚠️ No community platforms configured")
