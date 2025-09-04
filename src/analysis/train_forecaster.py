"""Train referendum outcome forecaster model."""
from __future__ import annotations

from pathlib import Path
import json
from typing import Dict, Tuple, List

import numpy as np
import pandas as pd

try:  # Prefer absolute import so tests can patch via ``src.data_processing``
    from src.data_processing.data_loader import load_governance_data
except Exception:  # pragma: no cover - fallback for runtime package layout
    from data_processing.data_loader import load_governance_data

MODEL_PATH = Path(__file__).resolve().parents[2] / "models" / "referendum_model.json"


def _prepare_features(df: pd.DataFrame) -> Tuple[pd.DataFrame, np.ndarray, List[str]]:
    """Return feature matrix ``X``, target ``y`` and feature names.

    The function derives commonly used referendum features from ``df`` and
    gracefully falls back to zeros when data is missing.  Supported features:

    ``approval_rate``  – ayes divided by total voted DOT
    ``turnout``        – participants divided by eligible DOT
    ``sentiment``            – sentiment score from sentiment analysis (column
                                name ``sentiment_score`` or ``sentiment``)
    ``trending``             – trending topic metric (column ``trend_score`` or
                                ``trending_score``)
    ``source_sentiment_avg`` – pre-computed average sentiment across sources
    ``comment_turnout_trend``– turnout trend derived from historical comments
    """

    df = df.copy()
    y = df.get("Status", pd.Series([], dtype=str)).astype(str).str.lower().eq("executed").astype(float)

    # Approval rate
    if {"ayes_amount", "Total_Voted_DOT"}.issubset(df.columns):
        approval_rate = (df["ayes_amount"].astype(float) / df["Total_Voted_DOT"].replace(0, np.nan)).fillna(0.0)
    else:
        approval_rate = pd.Series(0.0, index=df.index)

    # Turnout
    if "Voted_percentage" in df.columns:
        turnout = (df["Voted_percentage"].astype(float) / 100.0).fillna(0.0)
    elif {"Participants", "Eligible_DOT"}.issubset(df.columns):
        turnout = (df["Participants"].astype(float) / df["Eligible_DOT"].replace(0, np.nan)).fillna(0.0)
    else:
        turnout = pd.Series(0.0, index=df.index)

    sentiment = df.get("sentiment_score")
    if sentiment is None:
        sentiment = df.get("sentiment")
    if sentiment is None:
        sentiment = pd.Series(0.0, index=df.index)
    sentiment = sentiment.astype(float).fillna(0.0)

    trending = df.get("trend_score")
    if trending is None:
        trending = df.get("trending_score")
    if trending is None:
        trending = pd.Series(0.0, index=df.index)
    trending = trending.astype(float).fillna(0.0)

    source_avg = df.get("source_sentiment_avg")
    if source_avg is None:
        source_avg = pd.Series(0.0, index=df.index)
    source_avg = source_avg.astype(float).fillna(0.0)

    comment_trend = df.get("comment_turnout_trend")
    if comment_trend is None:
        comment_trend = pd.Series(0.0, index=df.index)
    comment_trend = comment_trend.astype(float).fillna(0.0)

    features = pd.DataFrame(
        {
            "approval_rate": approval_rate,
            "turnout": turnout,
            "sentiment": sentiment,
            "trending": trending,
            "source_sentiment_avg": source_avg,
            "comment_turnout_trend": comment_trend,
        }
    )
    return features, y.to_numpy(), list(features.columns)


def train_model(df: pd.DataFrame) -> Dict[str, Dict[str, float]]:
    """Fit a logistic regression model and return parameters.

    Parameters
    ----------
    df:
        Historical referendum DataFrame with outcome labels and feature data.
    """

    X, y, names = _prepare_features(df)
    if len(y) == 0:
        return {"intercept": 0.0, "coefficients": {}}

    # Convert binary outcomes to log-odds target
    eps = 1e-6
    y = np.clip(y, eps, 1 - eps)
    z = np.log(y / (1 - y))

    X_design = np.column_stack([np.ones(len(X)), X.to_numpy()])
    coeffs, *_ = np.linalg.lstsq(X_design, z, rcond=None)
    intercept = float(coeffs[0])
    weights = {name: float(c) for name, c in zip(names, coeffs[1:])}
    return {"intercept": intercept, "coefficients": weights}


def train_and_save() -> Dict[str, Dict[str, float]]:
    """Load governance data, train the model and persist parameters."""
    df = load_governance_data(sheet_name="Referenda")
    if isinstance(df, dict):
        df = next(iter(df.values()))
    model = train_model(df)
    MODEL_PATH.parent.mkdir(parents=True, exist_ok=True)
    with MODEL_PATH.open("w") as f:
        json.dump(model, f, indent=2)
    return model


if __name__ == "__main__":  # pragma: no cover - manual execution helper
    mdl = train_and_save()
    print(f"Saved model to {MODEL_PATH}")
