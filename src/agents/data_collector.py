"""Centralised data collection utilities."""
from __future__ import annotations

import datetime as dt
import os
import re
from collections import Counter
from typing import Any, Dict, Callable

import pandas as pd

from data_processing.social_media_scraper import (
    collect_recent_messages,
    flatten_forum_topic,
)
from data_processing.news_fetcher import fetch_and_summarise_news
from data_processing.blockchain_cache import (
    get_recent_blocks_cached,
    SUBSTRATE_RPC,
)
from data_processing.evm_data_fetcher import fetch_evm_blocks
from analysis.blockchain_metrics import summarise_blocks, summarise_evm_blocks
from data_processing.proposal_store import ROOT, XLSX_PATH


class DataCollector:
    """Aggregate external data sources for the pipeline."""

    @staticmethod
    def collect(
        msg_fn: Callable[[], Dict[str, list[Any]]] = collect_recent_messages,
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
        messages = msg_fn() or {}
        for src in list(messages.keys()):
            if not messages[src]:
                print(f"[warn] {src} returned no content; skipping")
                del messages[src]
        if not messages:
            print("[warn] no social messages collected")

        print("🔄 Fetching news …")
        news = news_fn() or {}
        if not isinstance(news, dict) or not news.get("articles"):
            print("[warn] news source returned no articles; skipping")
            news = {}

        print("🔄 Fetching on-chain data …")
        blocks = block_fn() or []
        if not blocks:
            print("[warn] no on-chain data fetched")

        # ------------------------------------------------------------------
        # Compute simple source statistics
        # ------------------------------------------------------------------
        update_freq = {
            "chat": "Real time",
            "forum": "Daily",
            "news": "Hourly",
            "governance": "Every Run",
            "onchain": "~6 sec",
        }
        platform_map = {
            "chat": "X (@PolkadotNetwork), Reddit (r/Polkadot)",
            "forum": "https://forum.polkadot.network",
            "news": (
                "https://cryptorank.io/news/polkadot; "
                "https://www.binance.com/en/square/post"
            ),
            "governance": str(XLSX_PATH.relative_to(ROOT)),
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
            "onchain": _env_weight("DATA_WEIGHT_CHAIN"),
            "governance": _env_weight("DATA_WEIGHT_GOVERNANCE"),
        }

        def _to_text(item: Any) -> str:
            if isinstance(item, dict):
                return flatten_forum_topic(item)
            return str(item)

        def _engagement_factor(items: list[Any]) -> float:
            total = 0.0
            count = 0
            for it in items:
                if isinstance(it, dict):
                    likes = it.get("likes") or 0
                    comments = it.get("comments") or 0
                    try:
                        total += float(likes) + float(comments)
                        count += 1
                    except (TypeError, ValueError):
                        continue
            if count == 0:
                return 1.0
            avg = total / count
            return 1.0 + avg
        if stats is None:
            stats = {}
        stats.setdefault("data_sources", {})

        def _default_last3(count: int) -> dict[str, int]:
            today = dt.date.today()
            return {
                (today - dt.timedelta(days=i)).isoformat(): (count if i == 0 else 0)
                for i in range(3)
            }

        for source, texts in messages.items():
            count = len(texts)
            text_snippets = [_to_text(t) for t in texts]

            # Engagement-aware weighting
            engagement = _engagement_factor(texts)
            weights[source] = weights.get(source, 1.0) * engagement

            total_words = sum(len(t.split()) for t in text_snippets)
            avg_words = total_words / count if count else 0.0
            stats["data_sources"][source] = {
                "count": count,
                "avg_word_length": avg_words,
                "total_tokens": total_words,
                "update_frequency": update_freq.get(source, "unknown"),
                "platform": platform_map.get(source),
                "weight": weights.get(source, 1.0),
                "last_3d_count": _default_last3(count),
            }

        article_texts: list[str] = []
        if news.get("articles"):
            engagement = _engagement_factor(news.get("articles", []))
            weights["news"] = weights.get("news", 1.0) * engagement
            for art in news.get("articles", []):
                parts = [art.get("title", ""), art.get("body", "")]
                comments = art.get("comments", [])
                if isinstance(comments, list):
                    parts.extend(str(c) for c in comments)
                article_texts.append(" ".join(p for p in parts if p))
            news_count = len(article_texts)
            total_news_words = sum(len(t.split()) for t in article_texts)
            avg_news_words = total_news_words / news_count if news_count else 0.0
            stats["data_sources"]["news"] = {
                "count": news_count,
                "avg_word_length": avg_news_words,
                "total_tokens": total_news_words,
                "update_frequency": update_freq.get("news", "unknown"),
                "platform": platform_map.get("news"),
                "weight": weights.get("news", 1.0),
                "last_3d_count": _default_last3(news_count),
            }

        # On-chain source statistics
        block_count = len(blocks)
        extrinsic_counts = [
            b.get("extrinsics_count", len(b.get("extrinsics", []))) for b in blocks
        ]
        total_extrinsics = sum(extrinsic_counts)
        avg_extrinsics = total_extrinsics / block_count if block_count else 0.0
        rpc_url = os.getenv("SUBSTRATE_RPC", SUBSTRATE_RPC)
        doc_url = os.getenv(
            "CHAIN_DOC_URL", "https://wiki.polkadot.network/docs"
        )
        last3 = {
            (dt.date.today() - dt.timedelta(days=i)).isoformat(): 0 for i in range(3)
        }
        for blk in blocks:
            ts = blk.get("block_timestamp")
            if ts:
                day = dt.datetime.fromtimestamp(ts, dt.UTC).date().isoformat()
                if day in last3:
                    last3[day] += 1
        stats["data_sources"]["onchain"] = {
            "count": block_count,
            "avg_word_length": avg_extrinsics,
            "total_tokens": total_extrinsics,
            "update_frequency": update_freq.get("onchain", "unknown"),
            "platform": rpc_url,
            "weight": weights.get("onchain", 1.0),
            "rpc_url": rpc_url,
            "doc_url": doc_url,
            "last_3d_count": last3,
        }

        # Governance workbook statistics
        gov_count = 0
        gov_avg = 0.0
        gov_total = 0
        if XLSX_PATH.exists():
            try:
                sheets = pd.read_excel(XLSX_PATH, sheet_name=None)
                frames = sheets.values() if isinstance(sheets, dict) else [sheets]
                docs: list[str] = []
                for df in frames:
                    if not isinstance(df, pd.DataFrame) or df.empty:
                        continue
                    for _, row in df.iterrows():
                        text = " ".join(str(v) for v in row.dropna().astype(str))
                        if text.strip():
                            docs.append(text)
                gov_count = len(docs)
                if gov_count:
                    gov_total = sum(len(t.split()) for t in docs)
                    gov_avg = gov_total / gov_count
            except Exception:
                pass

        stats["data_sources"]["governance"] = {
            "count": gov_count,
            "avg_word_length": gov_avg,
            "total_tokens": gov_total,
            "update_frequency": update_freq.get("governance", "unknown"),
            "platform": platform_map.get("governance"),
            "weight": weights.get("governance", 1.0),
            "last_3d_count": _default_last3(gov_count),
        }

        def _extract_trends(
            msgs: Dict[str, list[Any]],
            articles: list[str],
            weight_map: Dict[str, float],
            stats_dict: Dict[str, Any],
        ) -> list[str]:
            # Filter out common stop words and HTML/CSS related terms
            stop_words = set(
                "the of a to and in for on with by is are be at it this that as from".split()
            )
            html_terms = {
                "style",
                "element",
                "node",
                "div",
                "span",
                "html",
                "body",
                "head",
                "script",
                "class",
                "id",
                "section",
                "css",
            }

            def _valid_token(tok: str) -> bool:
                return tok.isalpha() and tok not in stop_words and tok not in html_terms

            counter: Counter[str] = Counter()
            raw_counter: Counter[str] = Counter()

            # Helper to update counters from a list of tokens
            def _count_tokens(tokens: list[str], weight: float) -> None:
                for a, b in zip(tokens, tokens[1:]):
                    if _valid_token(a) and _valid_token(b):
                        phrase = f"{a} {b}"
                        counter[phrase] += weight
                        raw_counter[phrase] += 1

            for src, items in msgs.items():
                w = weight_map.get(src, 1.0)
                for item in items:
                    text = _to_text(item).lower()
                    tokens_all = re.findall(r"\b\w+\b", text)
                    tokens = [t for t in tokens_all if t.isalpha()]
                    _count_tokens(tokens, w)

            if articles:
                w = weight_map.get("news", 1.0)
                for art in articles:
                    tokens_all = re.findall(r"\b\w+\b", art.lower())
                    tokens = [t for t in tokens_all if t.isalpha()]
                    _count_tokens(tokens, w)

            min_freq = 2
            candidates = [
                (phrase, counter[phrase])
                for phrase, cnt in raw_counter.items()
                if cnt >= min_freq
            ]
            candidates.sort(key=lambda x: x[1], reverse=True)
            top = candidates[:5]
            stats_dict["trending_topics"] = {phrase: weight for phrase, weight in top}
            return [phrase for phrase, _ in top]

        trending_topics = _extract_trends(messages, article_texts, weights, stats)

        block_summary = summarise_blocks(blocks)
        evm_blocks: list = []

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
            evm_blocks = evm_fn() or []
            if not evm_blocks:
                print("[warn] no EVM block data fetched")
            evm_summary = summarise_evm_blocks(evm_blocks)
            block_summary.update({f"evm_{k}": v for k, v in evm_summary.items()})

        result = {
            "messages": messages,
            "news": news,
            "blocks": block_summary,
            "evm_blocks": evm_blocks,
            "stats": stats,
            "trending_topics": trending_topics,
        }

        return result
