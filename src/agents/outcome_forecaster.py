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


def _apply_model(model: dict, approval_rate: float, turnout: float) -> float:
    """Apply a simple logistic model to produce approval probability."""

    z = model.get("intercept", 0.0)
    coeffs = model.get("coefficients", {})
    z += coeffs.get("approval_rate", 0.0) * approval_rate
    z += coeffs.get("turnout", 0.0) * turnout
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

    # Apply trained model if available
    model = _load_model()
    if model is not None:
        try:
            approval_prob = _apply_model(model, approval_prob, turnout_estimate)
        except Exception:
            pass

    return {
        "approval_prob": approval_prob,
        "turnout_estimate": turnout_estimate,
    }
