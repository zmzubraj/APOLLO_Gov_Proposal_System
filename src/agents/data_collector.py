"""Centralised data collection utilities."""
from __future__ import annotations

from typing import Any, Dict, Callable

from data_processing.social_media_scraper import collect_recent_messages
from data_processing.news_fetcher import fetch_and_summarise_news
from data_processing.blockchain_cache import get_recent_blocks_cached


class DataCollector:
    """Aggregate external data sources for the pipeline."""

    @staticmethod
    def collect(
        msg_fn: Callable[[], list] = collect_recent_messages,
        news_fn: Callable[[], Dict[str, Any]] = fetch_and_summarise_news,
        block_fn: Callable[[], list] = get_recent_blocks_cached,
    ) -> Dict[str, Any]:
        """Return recent messages, news summary, and block data."""
        print("🔄 Collecting social sentiment …")
        messages = msg_fn()

        print("🔄 Fetching news …")
        news = news_fn()

        print("🔄 Fetching on-chain data …")
        blocks = block_fn()

        return {"messages": messages, "news": news, "blocks": blocks}
