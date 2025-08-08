"""Poll community platforms and run sentiment analysis.

This module retrieves recent messages from Discord, Telegram and Twitter,
feeds them into the shared sentiment analysis component and appends the
results to ``data/output/community_sentiment.jsonl``.  It exposes a
``run_loop`` function so it can easily be triggered via cron or similar.
"""
from __future__ import annotations

import json
import os
import time
from pathlib import Path
from typing import List

from analysis.sentiment_analysis import analyse_messages
from . import discord_bot, telegram_bot, twitter_bot

OUTPUT_FILE = Path(__file__).resolve().parents[2] / "data" / "output" / "community_sentiment.jsonl"


def fetch_messages() -> List[str]:
    """Collect recent messages from all configured platforms."""
    messages: List[str] = []
    # Discord
    channel_id = os.getenv("DISCORD_CHANNEL_ID")
    if channel_id:
        messages.extend(discord_bot.poll_messages(channel_id))
    # Telegram
    messages.extend(telegram_bot.poll_messages())
    # Twitter
    query = os.getenv("TWITTER_QUERY")
    if query:
        messages.extend(twitter_bot.poll_messages(query))
    return [m for m in messages if m]


def analyse_and_store() -> dict | None:
    """Fetch messages, run sentiment analysis and append to file."""
    msgs = fetch_messages()
    if not msgs:
        return None
    result = analyse_messages(msgs)
    result["timestamp"] = int(time.time())
    OUTPUT_FILE.parent.mkdir(parents=True, exist_ok=True)
    with OUTPUT_FILE.open("a", encoding="utf-8") as fh:
        fh.write(json.dumps(result) + "\n")
    return result


def run_loop(interval: int = 3600) -> None:
    """Continuously run :func:`analyse_and_store` every ``interval`` seconds."""
    while True:
        analyse_and_store()
        time.sleep(interval)


if __name__ == "__main__":
    run_loop()
