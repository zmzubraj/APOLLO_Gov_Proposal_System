"""Outcome forecasting agent."""
from __future__ import annotations

from pathlib import Path
from typing import Dict, Optional

import json
import numpy as np

try:  # Prefer absolute import so tests can patch via ``src.data_processing``
    from src.data_processing import referenda_updater
except Exception:  # pragma: no cover
    from data_processing import referenda_updater


MODEL_PATH = Path(__file__).resolve().parents[2] / "models" / "referendum_model.json"


def _load_model() -> Optional[dict]:
    """Load model parameters from the models directory.

    Returns ``None`` if the model file is missing or invalid.
    """

    try:
        with MODEL_PATH.open() as f:
            return json.load(f)
    except Exception:
        return None


def _apply_model(model: dict, features: Dict[str, float]) -> float:
    """Apply a logistic model defined by ``model`` to ``features``.

    Parameters
    ----------
    model:
        Mapping containing ``intercept`` and ``coefficients`` (a mapping of
        feature name to weight).
    features:
        Feature values keyed by name.  Any feature missing from the model's
        coefficients is ignored so the helper is forward compatible with new
        inputs.
    """

    z = model.get("intercept", 0.0)
    coeffs = model.get("coefficients", {})
    for name, value in features.items():
        z += coeffs.get(name, 0.0) * value
    return float(1.0 / (1.0 + np.exp(-z)))


def forecast_outcomes(context: Dict) -> Dict[str, float]:
    """Return naive forecasts for upcoming referendum outcomes."""

    approval_prob = 0.5
    turnout_estimate = 0.0
    turnout_trend = 0.0
    try:
        stats = referenda_updater.load_historical_rates()
        approval_prob = stats.get("approval_rate", approval_prob)
        turnout_estimate = stats.get("turnout", turnout_estimate)
        turnout_trend = stats.get("turnout_trend", turnout_trend)
    except Exception:
        pass

    approval_prob = float(max(0.0, min(1.0, approval_prob)))
    turnout_estimate = float(max(0.0, min(1.0, turnout_estimate)))

    # Sentiment may be provided either directly or within a nested structure
    sentiment_val = context.get("sentiment_score")
    if sentiment_val is None:
        sentiment_val = context.get("sentiment")
        if isinstance(sentiment_val, dict):
            sentiment_val = sentiment_val.get("sentiment_score") or sentiment_val.get("score")
    sentiment = float(sentiment_val or 0.0)

    # Per-source sentiment averages
    src_sent = context.get("source_sentiments") or context.get("sentiment_sources")
    source_sentiment_avg = 0.0
    source_sentiment_values = []
    if isinstance(src_sent, dict) and src_sent:
        try:
            source_sentiment_values = [float(v) for v in src_sent.values()]
            if source_sentiment_values:
                source_sentiment_avg = float(np.mean(source_sentiment_values))
        except Exception:
            source_sentiment_values = []
            source_sentiment_avg = 0.0

    trending_val = context.get("trend_score")
    if trending_val is None:
        trending_val = context.get("trending_score")
    if trending_val is None:
        trending_val = context.get("trending")
        if isinstance(trending_val, dict):
            trending_val = trending_val.get("score") or trending_val.get("trending_score")
    trending = float(trending_val or 0.0)

    # Turnout trends from historical comments
    comment_trend_val = context.get("comment_turnout_trend")
    if comment_trend_val is None:
        comment_trend_val = context.get("turnout_trends")
        if isinstance(comment_trend_val, dict):
            comment_trend_val = comment_trend_val.get("comments") or comment_trend_val.get("comment")
    comment_turnout_trend = float(comment_trend_val or 0.0)

    # Additional contextual features
    proposal_text = context.get("proposal_text")
    if proposal_text is None:
        proposal = context.get("proposal")
        if isinstance(proposal, dict):
            proposal_text = proposal.get("text") or proposal.get("proposal_text")
    try:
        proposal_length = float(len(str(proposal_text).split())) if proposal_text else 0.0
    except Exception:
        proposal_length = 0.0

    weight_val = context.get("engagement_weight")
    if weight_val is None:
        weight_val = context.get("sentiment", {})
        if isinstance(weight_val, dict):
            weight_val = weight_val.get("weight")
    engagement_weight = float(weight_val or 0.0)

    features = {
        "approval_rate": approval_prob,
        "turnout": turnout_estimate,
        "sentiment": sentiment,
        "trending": trending,
        "proposal_length": proposal_length,
        "engagement_weight": engagement_weight,
        "turnout_trend": turnout_trend,
        "source_sentiment_avg": source_sentiment_avg,
        "comment_turnout_trend": comment_turnout_trend,
    }

    # Apply trained model if available; otherwise fall back to a heuristic that
    # still incorporates contextual information so drafts with stronger
    # sentiment/trend signals diverge from the historical average.
    model = _load_model()
    model_applied = False
    if model is not None:
        try:
            approval_prob = _apply_model(model, features)
            model_applied = True
        except Exception:
            model_applied = False

    if not model_applied:
        # Heuristic adjustments around the historical approval baseline.
        adjustments = (
            0.18 * features["sentiment"]
            + 0.12 * features["source_sentiment_avg"]
            + 0.10 * features["trending"]
            + 0.15 * features["comment_turnout_trend"]
            + 0.08 * features["turnout_trend"]
            + 0.06 * (features["turnout"] - 0.5)
            + 0.07 * (features["engagement_weight"] - 0.5)
            + 0.03 * (features["proposal_length"] / 500.0)
        )
        approval_prob = approval_prob + adjustments

    approval_prob = float(max(0.0, min(1.0, approval_prob)))

    # Draft-specific uncertainty estimates use turnout volatility, sentiment
    # dispersion and engagement weight to modulate the margin of error.  Higher
    # volatility and disagreement inflate the margin, while stronger engagement
    # reduces it.
    sentiment_spread = 0.0
    if len(source_sentiment_values) > 1:
        sentiment_spread = float(np.std(source_sentiment_values))
    elif source_sentiment_values:
        sentiment_spread = float(abs(source_sentiment_values[0] - sentiment) * 0.5)
    else:
        sentiment_spread = float(abs(sentiment) * 0.3)

    turnout_volatility = abs(features["turnout_trend"]) + abs(features["comment_turnout_trend"])
    engagement_factor = float(max(0.0, min(1.0, features["engagement_weight"])) if not np.isnan(features["engagement_weight"]) else 0.0)

    base_margin = 0.08 + 0.22 * turnout_volatility + 0.12 * sentiment_spread
    base_margin *= 1.0 - 0.35 * engagement_factor
    margin_of_error = float(max(0.02, min(0.45, base_margin)))

    confidence = 1.0 - margin_of_error
    confidence += 0.1 * abs(features["sentiment"]) + 0.05 * abs(features["source_sentiment_avg"])
    confidence = float(max(0.05, min(0.95, confidence)))

    return {
        "approval_prob": approval_prob,
        "turnout_estimate": turnout_estimate,
        "margin_of_error": margin_of_error,
        "confidence": confidence,
    }
