"""Context generation utilities."""
from __future__ import annotations

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


def _fetch_semantic_snippets(query: str, limit: int = 5) -> list[str]:
    """Retrieve snippets most similar to ``query`` using embeddings."""
    if not query:
        return []

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
        return []

    try:
        query_vec = ollama_api.embed_text(query)
    except Exception:
        return []

    scored: List[Tuple[float, str]] = []
    for text in candidates:
        try:
            vec = ollama_api.embed_text(text)
        except Exception:
            continue
        score = _cosine_similarity(query_vec, vec)
        scored.append((score, text))

    scored.sort(key=lambda t: t[0], reverse=True)
    return [text for _, text in scored[:limit]]


def _summarise(snippets: list[str]) -> str:
    """Summarise ``snippets`` using the LLM with a naive fallback."""
    prompt = "Summarise the following snippets:\n" + "\n".join(snippets)
    try:
        return ollama_api.generate_completion(prompt)
    except Exception:
        return " ".join(snippets)[:500]


def build_context(
    sentiment: Dict[str, Any],
    news: Dict[str, Any],
    chain_kpis: Dict[str, Any],
    gov_kpis: Dict[str, Any],
    kb_snippets: list[str] | None = None,
    kb_query: str | None = None,
    *,
    dedup_snippets: bool = True,
    summarise_snippets: bool = False,
) -> Dict[str, Any]:
    """Consolidate disparate inputs into a single context dictionary."""

    snippets = kb_snippets or []
    if not snippets and kb_query:
        snippets = _fetch_semantic_snippets(kb_query)

    if dedup_snippets:
        snippets = _dedup(snippets)
    summary = _summarise(snippets) if summarise_snippets and snippets else ""

    context = {
        "timestamp_utc": utc_now_iso(),
        "sentiment": sentiment,
        "news": news,
        "chain_kpis": chain_kpis,
        "governance_kpis": gov_kpis,
        "kb_snippets": snippets,
        "kb_summary": summary,
    }

    # Persist for audit trail
    proposal_store.record_context(context)
    return context
