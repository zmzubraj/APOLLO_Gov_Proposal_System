"""Context generation utilities."""
from __future__ import annotations

import os
from math import sqrt
from typing import Any, Dict, Iterable, List, Tuple

from utils.helpers import utc_now_iso
from data_processing import proposal_store
from llm import ollama_api


def _dedup(snippets: Iterable[str]) -> list[str]:
    """Return snippets with duplicates removed while preserving order."""
    seen = set()
    deduped: list[str] = []
    for s in snippets:
        s = s.strip()
        if s and s not in seen:
            seen.add(s)
            deduped.append(s)
    return deduped


def _cosine_similarity(a: List[float], b: List[float]) -> float:
    """Compute cosine similarity between two vectors."""
    if not a or not b:
        return 0.0
    dot = sum(x * y for x, y in zip(a, b))
    norm_a = sqrt(sum(x * x for x in a))
    norm_b = sqrt(sum(y * y for y in b))
    if norm_a == 0 or norm_b == 0:
        return 0.0
    return dot / (norm_a * norm_b)


def _fetch_semantic_snippets(query: str, limit: int = 5) -> Tuple[list[str], bool]:
    """Retrieve snippets most similar to ``query`` using embeddings.

    Returns a tuple of (snippets, embedded) where ``embedded`` indicates
    whether the embedding lookups succeeded for both the query and at least one
    candidate snippet.
    """
    if not query:
        return [], False

    proposals = proposal_store.load_proposals()
    contexts = proposal_store.load_contexts()

    candidates: list[str] = []
    if not proposals.empty and "proposal_text" in proposals.columns:
        candidates.extend(
            proposals["proposal_text"].dropna().astype(str).tolist()
        )
    if not contexts.empty and "context_json" in contexts.columns:
        candidates.extend(
            contexts["context_json"].dropna().astype(str).tolist()
        )

    if not candidates:
        return [], False

    try:
        query_vec = ollama_api.embed_text(query)
    except Exception:
        return [], False

    scored: List[Tuple[float, str]] = []
    embedded_snippet = False
    for text in candidates:
        try:
            vec = ollama_api.embed_text(text)
            embedded_snippet = True
        except Exception:
            continue
        score = _cosine_similarity(query_vec, vec)
        scored.append((score, text))

    if not embedded_snippet:
        return [], False

    scored.sort(key=lambda t: t[0], reverse=True)
    return [text for _, text in scored[:limit]], True


def _summarise(snippets: list[str]) -> str:
    """Summarise ``snippets`` using the LLM with a naive fallback."""
    prompt = "Summarise the following snippets:\n" + "\n".join(snippets)
    try:
        return ollama_api.generate_completion(prompt)
    except Exception:
        return " ".join(snippets)[:500]


def _env_weight(var: str) -> float:
    """Fetch a numeric weight from ``var`` environment variable."""
    try:
        return float(os.getenv(var, "1"))
    except ValueError:
        return 1.0


def _apply_weight(data: Any, weight: float) -> Any:
    """Recursively multiply numeric values in ``data`` by ``weight``."""
    if isinstance(data, dict):
        return {k: _apply_weight(v, weight) for k, v in data.items()}
    if isinstance(data, list):
        return [_apply_weight(v, weight) for v in data]
    if isinstance(data, (int, float)):
        return data * weight
    return data


def build_context(
    sentiment: Dict[str, Any],
    news: Dict[str, Any],
    chain_kpis: Dict[str, Any],
    gov_kpis: Dict[str, Any],
    kb_snippets: list[str] | None = None,
    kb_query: str | None = None,
    *,
    trending_topics: list[str] | None = None,
    dedup_snippets: bool = True,
    summarise_snippets: bool = False,
) -> Dict[str, Any]:
    """Consolidate disparate inputs into a single context dictionary."""

    snippets = kb_snippets or []
    embedded = False
    if not snippets and kb_query:
        snippets, embedded = _fetch_semantic_snippets(kb_query)
    elif snippets:
        embedded = True

    if dedup_snippets:
        snippets = _dedup(snippets)
    summary = _summarise(snippets) if summarise_snippets and snippets else ""

    # Apply weights to each component
    chat_w = _env_weight("DATA_WEIGHT_CHAT")
    forum_w = _env_weight("DATA_WEIGHT_FORUM")
    sentiment_w = (chat_w + forum_w) / 2
    news_w = _env_weight("DATA_WEIGHT_NEWS")
    chain_w = _env_weight("DATA_WEIGHT_CHAIN")
    gov_w = _env_weight("DATA_WEIGHT_GOVERNANCE")

    weighted_sentiment = _apply_weight(sentiment, sentiment_w)
    weighted_news = _apply_weight(news, news_w)
    weighted_chain = _apply_weight(chain_kpis, chain_w)
    weighted_gov = _apply_weight(gov_kpis, gov_w)

    context = {
        "timestamp_utc": utc_now_iso(),
        "sentiment": weighted_sentiment,
        "news": weighted_news,
        "chain_kpis": weighted_chain,
        "governance_kpis": weighted_gov,
        "trending_topics": trending_topics or [],
        "kb_snippets": snippets,
        "kb_summary": summary,
        "kb_embedded": embedded,
    }

    # Persist for audit trail
    proposal_store.record_context(context)
    return context
