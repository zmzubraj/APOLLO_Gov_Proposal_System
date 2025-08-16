"""Centralised data collection utilities."""
from __future__ import annotations

import os
from typing import Any, Dict, Callable

from data_processing.social_media_scraper import collect_recent_messages
from data_processing.news_fetcher import fetch_and_summarise_news
from data_processing.blockchain_cache import (
    get_recent_blocks_cached,
    SUBSTRATE_RPC,
)
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
            "chat": "Real time",
            "forum": "Daily",
            "news": "Hourly",
            "governance": "Every Run",
            "chain": "~6 sec",
        }
        platform_map = {
            "chat": "X (@PolkadotNetwork), Reddit (r/Polkadot)",
            "forum": "https://forum.polkadot.network",
            "news": (
                "https://cryptorank.io/news/polkadot; "
                "https://www.binance.com/en/square/post"
            ),
        }
        # ------------------------------------------------------------------
        # Optional per-source weighting from environment variables
        # ------------------------------------------------------------------
        def _env_weight(var: str) -> float:
            try:
                return float(os.getenv(var, "1"))
            except ValueError:
                return 1.0

        weights = {
            "chat": _env_weight("DATA_WEIGHT_CHAT"),
            "forum": _env_weight("DATA_WEIGHT_FORUM"),
            "news": _env_weight("DATA_WEIGHT_NEWS"),
            "chain": _env_weight("DATA_WEIGHT_CHAIN"),
            "governance": _env_weight("DATA_WEIGHT_GOVERNANCE"),
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
                "platform": platform_map.get(source),
                "weight": weights.get(source, 1.0),
            }

        print("🔄 Fetching news …")
        news = news_fn()

        news_count = len(news.get("digest", [])) if isinstance(news, dict) else 0
        avg_news_words = (
            sum(len(t.split()) for t in news.get("digest", [])) / news_count
            if news_count
            else 0.0
        )
        stats["data_sources"]["news"] = {
            "count": news_count,
            "avg_word_length": avg_news_words,
            "update_frequency": update_freq.get("news", "unknown"),
            "platform": platform_map.get("news"),
            "weight": weights.get("news", 1.0),
        }

        print("🔄 Fetching on-chain data …")
        blocks = block_fn()

        # On-chain source statistics
        block_count = len(blocks)
        avg_extrinsics = (
            sum(
                b.get("extrinsics_count", len(b.get("extrinsics", [])))
                for b in blocks
            )
            / block_count
            if block_count
            else 0.0
        )
        rpc_url = os.getenv("SUBSTRATE_RPC", SUBSTRATE_RPC)
        stats["data_sources"]["chain"] = {
            "count": block_count,
            "avg_word_length": avg_extrinsics,
            "update_frequency": update_freq.get("chain", "unknown"),
            "platform": rpc_url,
            "weight": weights.get("chain", 1.0),
        }

        # Include governance placeholder so that weight information is surfaced
        stats["data_sources"].setdefault(
            "governance",
            {
                "count": 0,
                "avg_word_length": 0.0,
                "update_frequency": update_freq.get("governance", "unknown"),
                "platform": None,
                "weight": weights.get("governance", 1.0),
            },
        )

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
