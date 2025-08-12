"""Outcome forecasting agent."""
from __future__ import annotations

from typing import Dict

import pandas as pd

try:  # Prefer absolute import so tests can patch via ``src.data_processing``
    from src.data_processing.data_loader import load_governance_data
except Exception:  # pragma: no cover
    from data_processing.data_loader import load_governance_data


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
    return {
        "approval_prob": approval_prob,
        "turnout_estimate": turnout_estimate,
    }
