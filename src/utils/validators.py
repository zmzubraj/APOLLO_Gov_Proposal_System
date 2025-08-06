"""
validators.py
--------------
Lightweight schema / sanity checks for every data blob in the pipeline.
All functions return True on success or raise ValueError with details.
"""

from __future__ import annotations
from typing import Dict, Any


# ────────────────────────────────────────────────────────────────────────────
def _require_keys(obj: Dict[str, Any], keys: set[str], label: str):
    missing = keys - obj.keys()
    if missing:
        raise ValueError(f"{label}: missing keys {missing}")


# ────────────────────────────────────────────────────────────────────────────
def validate_sentiment(d: Dict[str, Any]) -> bool:
    _require_keys(d, {"sentiment_score", "summary", "key_topics"}, "sentiment")
    if not (-1 <= d["sentiment_score"] <= 1):
        raise ValueError("sentiment_score outside [-1,1]")
    return True


def validate_news(d: Dict[str, Any]) -> bool:
    _require_keys(d, {"digest", "risks"}, "news")
    if not isinstance(d["digest"], list):
        raise ValueError("news.digest should be list")
    return True


def validate_chain_kpis(d: Dict[str, Any]) -> bool:
    _require_keys(
        d,
        {
            "daily_tx_count",
            "daily_total_fees_DOT",
            "avg_tx_per_block",
            "avg_fee_per_tx_DOT",
            "busiest_hour_utc",
        },
        "chain_kpis",
    )
    return True


def validate_governance_kpis(d: Dict[str, Any]) -> bool:
    expected = {
        "total_referenda",
        "executed_pct",
        "rejected_pct",
        "avg_turnout_pct",
        "median_turnout_pct",
        "avg_participants",
        "avg_duration_days",
        "monthly_counts",
        "top_keywords",
    }
    _require_keys(d, expected, "governance_kpis")
    return True


def validate_predictions(d: Dict[str, Any]) -> bool:
    """Ensure forecasting output contains probabilities in [0,1]."""
    _require_keys(d, {"approval_probability", "turnout"}, "predictions")
    if not (0 <= d["approval_probability"] <= 1):
        raise ValueError("approval_probability outside [0,1]")
    if not (0 <= d["turnout"] <= 1):
        raise ValueError("turnout outside [0,1]")
    return True

