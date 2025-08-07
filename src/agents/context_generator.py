"""Context generation utilities."""
from __future__ import annotations

from typing import Dict, Any

from utils.helpers import utc_now_iso


def build_context(
    sentiment: Dict[str, Any],
    news: Dict[str, Any],
    chain_kpis: Dict[str, Any],
    gov_kpis: Dict[str, Any],
) -> Dict[str, Any]:
    """Consolidate disparate inputs into a single context dictionary."""
    return {
        "timestamp_utc": utc_now_iso(),
        "sentiment": sentiment,
        "news": news,
        "chain_kpis": chain_kpis,
        "governance_kpis": gov_kpis,
    }
