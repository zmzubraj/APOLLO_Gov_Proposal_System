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
        msg_fn: Callable[[], list] = collect_recent_messages,
        news_fn: Callable[[], Dict[str, Any]] = fetch_and_summarise_news,
        block_fn: Callable[[], list] = get_recent_blocks_cached,
        evm_fn: Callable[[], list] | None = None,
    ) -> Dict[str, Any]:
        """Return recent messages, news summary, and block data.

        If the environment variable ``ENABLE_EVM_FETCH`` is set to ``"true"``
        (case-insensitive), EVM block data will also be collected. A custom
        function can be supplied via ``evm_fn``; otherwise a default fetcher
        using :func:`data_processing.evm_data_fetcher.fetch_evm_blocks` is
        invoked. Results are stored under the ``"evm_blocks"`` key.
        """
        print("🔄 Collecting social sentiment …")
        messages = msg_fn()

        print("🔄 Fetching news …")
        news = news_fn()

        print("🔄 Fetching on-chain data …")
        blocks = block_fn()

        result = {"messages": messages, "news": news, "blocks": blocks}

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
