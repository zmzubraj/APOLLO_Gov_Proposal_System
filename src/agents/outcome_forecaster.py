"""Outcome forecasting agent."""
from __future__ import annotations

from pathlib import Path
from typing import Dict, Optional

import json
import numpy as np
import pandas as pd

try:  # Prefer absolute import so tests can patch via ``src.data_processing``
    from src.data_processing.data_loader import load_governance_data
except Exception:  # pragma: no cover
    from data_processing.data_loader import load_governance_data


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
    try:
        df = load_governance_data(sheet_name="Referenda")
    except Exception:
        df = pd.DataFrame()

    approval_prob = 0.5
    turnout_estimate = 0.0

    try:
        if not df.empty:
            if "Status" in df.columns and len(df):
                approved = df["Status"].astype(str).str.lower().eq("executed").sum()
                approval_prob = approved / len(df)
            if "Voted_percentage" in df.columns:
                turnout_estimate = df["Voted_percentage"].astype(float).mean() / 100.0
            elif {"Participants", "Eligible_DOT"}.issubset(df.columns):
                turnout_estimate = (
                    (df["Participants"].astype(float) / df["Eligible_DOT"].replace(0, pd.NA))
                    .fillna(0)
                    .mean()
                )
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

    trending_val = context.get("trend_score")
    if trending_val is None:
        trending_val = context.get("trending_score")
    if trending_val is None:
        trending_val = context.get("trending")
        if isinstance(trending_val, dict):
            trending_val = trending_val.get("score") or trending_val.get("trending_score")
    trending = float(trending_val or 0.0)

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

    turnout_trend = 0.0
    try:
        if not df.empty:
            if "Voted_percentage" in df.columns:
                turnouts = df["Voted_percentage"].astype(float) / 100.0
            elif {"Participants", "Eligible_DOT"}.issubset(df.columns):
                turnouts = (
                    df["Participants"].astype(float)
                    / df["Eligible_DOT"].replace(0, pd.NA).astype(float)
                ).fillna(0)
            else:
                turnouts = pd.Series([], dtype=float)
            if len(turnouts) >= 2:
                recent = turnouts.tail(min(5, len(turnouts)))
                x = np.arange(len(recent))
                turnout_trend = float(np.polyfit(x, recent, 1)[0])
    except Exception:
        turnout_trend = 0.0

    # Apply trained model if available
    model = _load_model()
    if model is not None:
        try:
            features = {
                "approval_rate": approval_prob,
                "turnout": turnout_estimate,
                "sentiment": sentiment,
                "trending": trending,
                "proposal_length": proposal_length,
                "engagement_weight": engagement_weight,
                "turnout_trend": turnout_trend,
            }
            approval_prob = _apply_model(model, features)
        except Exception:
            pass

    return {
        "approval_prob": float(max(0.0, min(1.0, approval_prob))),
        "turnout_estimate": turnout_estimate,
    }
