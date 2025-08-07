"""Context generation utilities."""
from __future__ import annotations

from typing import Dict, Any, Iterable

from utils.helpers import utc_now_iso


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


def _summarise(snippets: list[str]) -> str:
    """Naively summarise snippets by concatenation.

    A lightweight fallback is used instead of an LLM so tests remain
    deterministic.  Callers can post-process this summary further if desired.
    """
    return " ".join(snippets)[:500]


def build_context(
    sentiment: Dict[str, Any],
    news: Dict[str, Any],
    chain_kpis: Dict[str, Any],
    gov_kpis: Dict[str, Any],
    kb_snippets: list[str] | None = None,
    *,
    dedup_snippets: bool = True,
    summarise_snippets: bool = False,
) -> Dict[str, Any]:
    """Consolidate disparate inputs into a single context dictionary.

    Parameters
    ----------
    dedup_snippets:
        Remove duplicate snippets before inclusion.
    summarise_snippets:
        If True, a ``kb_summary`` field containing a simple concatenation of
        snippets is added.
    """
    snippets = kb_snippets or []
    if dedup_snippets:
        snippets = _dedup(snippets)
    summary = _summarise(snippets) if summarise_snippets and snippets else ""
    return {
        "timestamp_utc": utc_now_iso(),
        "sentiment": sentiment,
        "news": news,
        "chain_kpis": chain_kpis,
        "governance_kpis": gov_kpis,
        "kb_snippets": snippets,
        "kb_summary": summary,
    }
