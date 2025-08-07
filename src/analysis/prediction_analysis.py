import pandas as pd
from typing import Dict

from src.data_processing.data_loader import load_governance_data


def forecast_outcomes(context: Dict) -> Dict[str, float]:
    """Return naive forecasts for upcoming referendum outcomes.

    The function inspects historical referendum data stored in the
    ``PKD Governance Data.xlsx`` workbook and computes two simple metrics:

    ``approval_prob``
        Fraction of past referenda that executed successfully.
    ``turnout_estimate``
        Average voter turnout (participants / eligible) across historical
        referenda.

    Parameters
    ----------
    context: dict
        Unused currently but kept for future model features.

    Returns
    -------
    dict
        Dictionary with ``approval_prob`` and ``turnout_estimate`` keys.
    """
    try:
        df = load_governance_data(sheet_name="Referenda")
    except Exception:
        df = pd.DataFrame()

    approval_prob = 0.5
    turnout_estimate = 0.0

    try:
        if not df.empty:
            # Approval probability: share of executed referenda
            if "Status" in df.columns and len(df):
                approved = df["Status"].astype(str).str.lower().eq("executed").sum()
                approval_prob = approved / len(df)
            # Turnout: either provided percentage or compute from counts
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
