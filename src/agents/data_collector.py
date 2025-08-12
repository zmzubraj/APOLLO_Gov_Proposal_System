"""Centralised data collection utilities."""
from __future__ import annotations

import os
from typing import Any, Dict, Callable

from data_processing.social_media_scraper import collect_recent_messages
from data_processing.news_fetcher import fetch_and_summarise_news
from data_processing.blockchain_cache import get_recent_blocks_cached
from data_processing.evm_data_fetcher import fetch_evm_blocks


class DataCollector:
    """Aggregate external data sources for the pipeline."""

    @staticmethod
    def collect(
        msg_fn: Callable[[], Dict[str, list[str]]] = collect_recent_messages,
        news_fn: Callable[[], Dict[str, Any]] = fetch_and_summarise_news,
        block_fn: Callable[[], list] = get_recent_blocks_cached,
        evm_fn: Callable[[], list] | None = None,
        stats: Dict[str, Any] | None = None,
    ) -> Dict[str, Any]:
        """Return recent messages, news summary, block data and stats.

        Parameters are the same as before with the addition of ``stats`` which
        allows callers to provide a dictionary for metric aggregation. When not
        supplied, a new dictionary is created.  Any collected source statistics
        are added under ``stats['data_sources']`` and the dictionary is returned
        as part of the result for backwards compatibility.

        If the environment variable ``ENABLE_EVM_FETCH`` is set to ``"true"``
        (case-insensitive), EVM block data will also be collected. A custom
        function can be supplied via ``evm_fn``; otherwise a default fetcher
        using :func:`data_processing.evm_data_fetcher.fetch_evm_blocks` is
        invoked. Results are stored under the ``"evm_blocks"`` key.
        """
        print("🔄 Collecting social sentiment …")
        messages = msg_fn()

        # ------------------------------------------------------------------
        # Compute simple source statistics
        # ------------------------------------------------------------------
        update_freq = {
            "chat": "realtime",
            "forum": "daily",
            "news": "hourly",
        }
        if stats is None:
            stats = {}
        stats.setdefault("data_sources", {})
        for source, texts in messages.items():
            count = len(texts)
            avg_words = (
                sum(len(t.split()) for t in texts) / count if count else 0.0
            )
            stats["data_sources"][source] = {
                "count": count,
                "avg_word_length": avg_words,
                "update_frequency": update_freq.get(source, "unknown"),
            }

        print("🔄 Fetching news …")
        news = news_fn()

        print("🔄 Fetching on-chain data …")
        blocks = block_fn()

        result = {
            "messages": messages,
            "news": news,
            "blocks": blocks,
            "stats": stats,
        }

        enable_evm = os.getenv("ENABLE_EVM_FETCH", "false").lower() == "true"
        if enable_evm:
            if evm_fn is None:
                rpc = os.getenv("EVM_RPC_URL", "http://localhost:8545")
                start = os.getenv("EVM_START_BLOCK")
                end = os.getenv("EVM_END_BLOCK")
                start_block = int(start) if start else None
                end_block = int(end) if end else None

                def evm_fn() -> list:
                    return fetch_evm_blocks(rpc, start_block, end_block)

            print("🔄 Fetching EVM chain data …")
            result["evm_blocks"] = evm_fn()

        return result
