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


def _summarise(
    snippets: list[str],
    *,
    temperature: float | None = None,
    max_tokens: int | None = None,
    timeout: float | None = None,
) -> str:
    """Summarise ``snippets`` using the LLM with a naive fallback."""
    prompt = "Summarise the following snippets:\n" + "\n".join(snippets)
    temperature = (
        temperature
        if temperature is not None
        else float(os.getenv("SUMMARY_TEMPERATURE", "0.2"))
    )
    max_tokens = (
        max_tokens
        if max_tokens is not None
        else int(os.getenv("SUMMARY_MAX_TOKENS", "1024"))
    )
    timeout = (
        timeout
        if timeout is not None
        else float(os.getenv("SUMMARY_TIMEOUT", os.getenv("OLLAMA_TIMEOUT", "240")))
    )
    try:
        return ollama_api.generate_completion(
            prompt, temperature=temperature, max_tokens=max_tokens, timeout=timeout
        )
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
    old_referenda: Dict[str, Any] | None = None,
    trending_topics: list[str] | None = None,
    dedup_snippets: bool = True,
    summarise_snippets: bool = False,
    source_weight: Dict[str, Dict[str, float]] | None = None,
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

    source_weight = source_weight or {}

    def _info(key: str, default_source: str, env_var: str) -> tuple[str, float]:
        info = source_weight.get(key, {}) if isinstance(source_weight, dict) else {}
        src = info.get("source", default_source) if isinstance(info, dict) else default_source
        w = info.get("weight") if isinstance(info, dict) else None
        if w is None:
            if key == "sentiment":
                chat_w = _env_weight("DATA_WEIGHT_CHAT")
                forum_w = _env_weight("DATA_WEIGHT_FORUM")
                w = (chat_w + forum_w) / 2
            else:
                w = _env_weight(env_var)
        return src, w

    def _wrap(data: Any, src: str, w: float) -> Dict[str, Any]:
        weighted = _apply_weight(data, w)
        if isinstance(weighted, dict):
            return {"source": src, "weight": w, **weighted}
        return {"source": src, "weight": w, "value": weighted}

    sent_src, sent_w = _info("sentiment", "sentiment", "DATA_WEIGHT_CHAT")
    news_src, news_w = _info("news", "news", "DATA_WEIGHT_NEWS")
    chain_src, chain_w = _info("chain_kpis", "onchain", "DATA_WEIGHT_CHAIN")
    gov_src, gov_w = _info("governance_kpis", "governance", "DATA_WEIGHT_GOVERNANCE")
    old_src, old_w = _info("old_referenda", "old_referenda", "DATA_WEIGHT_OLD_REFERENDA")

    context = {
        "timestamp_utc": utc_now_iso(),
        "sentiment": _wrap(sentiment, sent_src, sent_w),
        "news": _wrap(news, news_src, news_w),
        "chain_kpis": _wrap(chain_kpis, chain_src, chain_w),
        "governance_kpis": _wrap(gov_kpis, gov_src, gov_w),
        "trending_topics": trending_topics or [],
        "kb_snippets": snippets,
        "kb_summary": summary,
        "kb_embedded": embedded,
    }

    if old_referenda:
        context["old_referenda"] = _wrap(old_referenda, old_src, old_w)

    # Persist for audit trail – ignore failures from missing dependencies
    try:
        proposal_store.record_context(context)
    except Exception:
        pass
    # Retrieve and merge historical proposals based on trending topics
    historical = proposal_store.retrieve_recent(trending_topics or [])
    if historical:
        context["historical_proposals"] = historical
    return context
