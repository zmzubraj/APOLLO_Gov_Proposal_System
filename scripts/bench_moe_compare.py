"""
Compare old vs new Margin of Error and confidence across a few scenarios.

This script re-implements the MoE logic from the forecaster to avoid
importing third-party dependencies. It simulates the same feature extraction
used for MoE (volatility, sentiment dispersion, engagement, N-effective),
and computes both the previous and updated formulations.

Run:
  python scripts/bench_moe_compare.py
"""
from __future__ import annotations

from math import sqrt
from typing import Dict, List, Any


def _mean(xs: List[float]) -> float:
    return sum(xs) / len(xs) if xs else 0.0


def _pop_std(xs: List[float]) -> float:
    if not xs:
        return 0.0
    m = _mean(xs)
    return sqrt(sum((x - m) ** 2 for x in xs) / len(xs))


def _extract_context_features(context: Dict[str, Any]) -> Dict[str, float | List[float] | str | int]:
    # Historical baselines (stubbed; set to realistic values)
    approval_rate = float(context.get("baseline_approval_rate", 0.52))
    turnout_estimate = float(context.get("baseline_turnout", 0.30))
    turnout_trend = float(context.get("baseline_turnout_trend", 0.0))

    # Sentiment
    sentiment_val = context.get("sentiment_score")
    if sentiment_val is None:
        sentiment_val = context.get("sentiment")
        if isinstance(sentiment_val, dict):
            sentiment_val = (
                sentiment_val.get("sentiment_score")
                or sentiment_val.get("score")
            )
    sentiment = float(sentiment_val or 0.0)

    # Per-source sentiment
    src_sent = context.get("source_sentiments") or context.get("sentiment_sources")
    source_sentiment_avg = 0.0
    source_sentiment_values: List[float] = []
    if isinstance(src_sent, dict) and src_sent:
        try:
            source_sentiment_values = [float(v) for v in src_sent.values()]
            if source_sentiment_values:
                source_sentiment_avg = float(_mean(source_sentiment_values))
        except Exception:
            source_sentiment_values = []
            source_sentiment_avg = 0.0

    # Trending
    trending_val = context.get("trend_score")
    if trending_val is None:
        trending_val = context.get("trending_score")
    if trending_val is None:
        trending_val = context.get("trending")
        if isinstance(trending_val, dict):
            trending_val = (
                trending_val.get("score") or trending_val.get("trending_score")
            )
    trending = float(trending_val or 0.0)

    # Comment/turnout trend
    comment_trend_val = context.get("comment_turnout_trend")
    if comment_trend_val is None:
        comment_trend_val = context.get("turnout_trends")
        if isinstance(comment_trend_val, dict):
            comment_trend_val = (
                comment_trend_val.get("comments") or comment_trend_val.get("comment")
            )
    comment_turnout_trend = float(comment_trend_val or 0.0)

    # Engagement weight
    weight_val = context.get("engagement_weight")
    if weight_val is None:
        weight_val = context.get("sentiment", {})
        if isinstance(weight_val, dict):
            weight_val = weight_val.get("weight")
    engagement_weight = float(weight_val or 0.0)

    # Primary source + coverage
    primary_source = None
    sent_wrap = context.get("sentiment")
    if isinstance(sent_wrap, dict):
        primary_source = sent_wrap.get("source")
        try:
            ctx_kb = float(sent_wrap.get("message_size_kb") or 0.0)
        except Exception:
            ctx_kb = 0.0
    else:
        ctx_kb = 0.0
    topics_n = 0
    try:
        topics_n = len(context.get("trending_topics", []) or [])
    except Exception:
        topics_n = 0
    snippets_n = 0
    try:
        snippets_n = len(context.get("kb_snippets", []) or [])
    except Exception:
        snippets_n = 0

    return {
        "approval_rate": float(max(0.0, min(1.0, approval_rate))),
        "turnout": float(max(0.0, min(1.0, turnout_estimate))),
        "turnout_trend": float(turnout_trend),
        "sentiment": float(sentiment),
        "source_sentiment_avg": float(source_sentiment_avg),
        "source_sentiment_values": source_sentiment_values,
        "trending": float(trending),
        "comment_turnout_trend": float(comment_turnout_trend),
        "engagement_weight": float(engagement_weight),
        "primary_source": str(primary_source or ""),
        "ctx_kb": float(ctx_kb),
        "topics_n": float(topics_n),
        "snippets_n": float(snippets_n),
    }


def _heuristic_prob(features: Dict[str, Any]) -> float:
    # Matches the heuristic adjustment path in the forecaster when no model.
    p = features["approval_rate"]
    p += (
        0.18 * features["sentiment"]
        + 0.12 * features["source_sentiment_avg"]
        + 0.10 * features["trending"]
        + 0.15 * features["comment_turnout_trend"]
        + 0.08 * features["turnout_trend"]
        + 0.06 * (features["turnout"] - 0.5)
        + 0.07 * (features["engagement_weight"] - 0.5)
        # proposal_length term omitted (not influential for MoE showcase)
    )
    return float(max(0.0, min(1.0, p)))


def _n_effective(features: Dict[str, Any]) -> float:
    base_by_src = {
        "forum": 250.0,
        "news": 200.0,
        "chat": 120.0,
        "onchain": 100.0,
        "governance": 220.0,
        "consolidated": 300.0,
    }
    base_n = base_by_src.get(features["primary_source"].lower(), 150.0)
    N = (
        base_n
        + 10.0 * features["ctx_kb"]
        + 20.0 * features["topics_n"]
        + 15.0 * features["snippets_n"]
    )
    try:
        N *= (1.0 + 0.5 * float(features["engagement_weight"]))
    except Exception:
        pass
    return float(max(30.0, min(5000.0, N)))


def _moe_old(features: Dict[str, Any], p: float) -> float:
    # Old heuristic inputs
    if len(features["source_sentiment_values"]) > 1:
        sentiment_spread = _pop_std(features["source_sentiment_values"])  # population std
    elif features["source_sentiment_values"]:
        sentiment_spread = abs(features["source_sentiment_values"][0] - features["sentiment"]) * 0.5
    else:
        sentiment_spread = abs(features["sentiment"]) * 0.3
    turnout_volatility = abs(features["turnout_trend"]) + abs(features["comment_turnout_trend"])
    engagement_factor = max(0.0, min(1.0, features["engagement_weight"]))

    base_margin = 0.08 + 0.22 * turnout_volatility + 0.12 * sentiment_spread
    base_margin *= 1.0 - 0.35 * engagement_factor
    margin_heuristic = max(0.02, min(0.45, base_margin))

    # Normal-approx MoE
    z = 1.96
    N_eff = _n_effective(features)
    moe_stat = z * (p * (1.0 - p)) ** 0.5 / (N_eff ** 0.5)

    return float(max(0.01, min(0.45, 0.5 * margin_heuristic + 0.5 * moe_stat)))


def _moe_new(features: Dict[str, Any], p: float) -> float:
    # New heuristic slightly softened
    if len(features["source_sentiment_values"]) > 1:
        sentiment_spread = _pop_std(features["source_sentiment_values"])  # population std
    elif features["source_sentiment_values"]:
        sentiment_spread = abs(features["source_sentiment_values"][0] - features["sentiment"]) * 0.5
    else:
        sentiment_spread = abs(features["sentiment"]) * 0.3
    turnout_volatility = abs(features["turnout_trend"]) + abs(features["comment_turnout_trend"])
    engagement_factor = max(0.0, min(1.0, features["engagement_weight"]))

    base_margin = 0.06 + 0.18 * turnout_volatility + 0.10 * sentiment_spread
    base_margin *= 1.0 - 0.35 * engagement_factor
    margin_heuristic = max(0.02, min(0.45, base_margin))

    # Wilson half-width
    N_eff = _n_effective(features)
    z = 1.96
    denom = 1.0 + (z * z) / N_eff
    center = (p + (z * z) / (2.0 * N_eff)) / denom
    radius = (z / denom) * ((p * (1.0 - p) / N_eff + (z * z) / (4.0 * (N_eff ** 2))) ** 0.5)
    wilson_low = max(0.0, center - radius)
    wilson_high = min(1.0, center + radius)
    moe_wilson = 0.5 * (wilson_high - wilson_low)
    if not (moe_wilson > 0.0):
        moe_wilson = z * (p * (1.0 - p)) ** 0.5 / (N_eff ** 0.5)

    # Blend by N
    decay_scale = 400.0
    w_heuristic = 1.0 / (1.0 + (N_eff / decay_scale))
    w_stat = 1.0 - w_heuristic
    margin = w_heuristic * margin_heuristic + w_stat * moe_wilson
    return float(max(0.01, min(0.45, margin)))


def _confidence_from_moe(moe: float, features: Dict[str, Any]) -> float:
    conf = 1.0 - moe
    conf += 0.05 * abs(features["sentiment"]) + 0.02 * abs(features["source_sentiment_avg"])
    return float(max(0.05, min(0.99, conf)))


def _format_pct(x: float) -> str:
    return f"{x * 100:.2f}%"


def run():
    scenarios: List[Dict[str, Any]] = [
        {
            "name": "Chat moderate + trending",
            "sentiment": {"source": "chat", "score": 0.25, "weight": 0.7, "message_size_kb": 50},
            "source_sentiments": {"chat": 0.25, "forum": 0.10},
            "trending_score": 0.15,
            "comment_turnout_trend": 0.10,
            "trending_topics": ["governance", "staking", "runtime"],
            "kb_snippets": ["a", "b", "c", "d"],
        },
        {
            "name": "Forum strong + high engagement",
            "sentiment": {"source": "forum", "score": 0.45, "weight": 0.9, "message_size_kb": 120},
            "source_sentiments": {"forum": 0.50, "chat": 0.35, "news": 0.20},
            "trending": {"score": 0.20},
            "comment_turnout_trend": 0.15,
            "trending_topics": ["treasury", "governance", "allocations", "contracts"],
            "kb_snippets": list("abcdefg"),
        },
        {
            "name": "Onchain negative + low engagement",
            "sentiment": {"source": "onchain", "score": -0.30, "weight": 0.3, "message_size_kb": 30},
            "source_sentiments": {"onchain": -0.30, "chat": -0.10},
            "trend_score": -0.05,
            "comment_turnout_trend": -0.08,
            "trending_topics": ["fees"],
            "kb_snippets": ["a"],
        },
        {
            "name": "Consolidated broad coverage",
            "sentiment": {"source": "consolidated", "score": 0.10, "weight": 0.8, "message_size_kb": 300},
            "source_sentiments": {"chat": 0.05, "forum": 0.15, "news": -0.05, "onchain": 0.00},
            "trending_score": 0.10,
            "comment_turnout_trend": 0.05,
            "trending_topics": ["gov", "kpi", "parachains", "auctions", "staking", "coretime"],
            "kb_snippets": [str(i) for i in range(15)],
        },
    ]

    headers = [
        "Scenario",
        "p",
        "N_eff",
        "Old MoE",
        "New MoE",
        "Delta MoE",
        "Old Conf",
        "New Conf",
        "Delta Conf",
    ]

    rows: List[List[str]] = []
    for sc in scenarios:
        f = _extract_context_features(sc)
        p = _heuristic_prob(f)
        N_eff = _n_effective(f)
        moe_old = _moe_old(f, p)
        moe_new = _moe_new(f, p)
        conf_old = _confidence_from_moe(moe_old, f)
        conf_new = _confidence_from_moe(moe_new, f)
        rows.append([
            sc["name"],
            f"{p:.3f}",
            f"{N_eff:.0f}",
            _format_pct(moe_old),
            _format_pct(moe_new),
            _format_pct(moe_new - moe_old),
            _format_pct(conf_old),
            _format_pct(conf_new),
            _format_pct(conf_new - conf_old),
        ])

    # Render a simple table
    widths = [max(len(h), *(len(r[i]) for r in rows)) for i, h in enumerate(headers)]
    fmt = " | ".join(f"{{:<{w}}}" for w in widths)
    sep = "-+-".join("-" * w for w in widths)
    print(fmt.format(*headers))
    print(sep)
    for r in rows:
        print(fmt.format(*r))


if __name__ == "__main__":
    run()
