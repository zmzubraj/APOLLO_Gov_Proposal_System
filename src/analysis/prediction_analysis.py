from __future__ import annotations
"""Simple outcome forecasting based on historical governance data.

Provides :func:`forecast_outcome` which estimates approval probability and
expected voter turnout for a new referendum.  The function attempts to load
historical OpenGov data via :func:`src.data_processing.data_loader.load_first_sheet`.
If the Excel dataset is unavailable or lacks the required columns, sensible
fallback values are returned.
"""

from typing import Dict, Any
import pandas as pd

from data_processing.data_loader import load_first_sheet


def _mean_turnout(df: pd.DataFrame) -> float:
    """Extract average turnout from the ``Voted_percentage`` column.

    The dataset sometimes stores percentages as 0-100 or 0-1.  We normalise to a
    0-1 range.
    """
    turnout = pd.to_numeric(df.get("Voted_percentage"), errors="coerce")
    turnout = turnout.dropna()
    if turnout.empty:
        return 0.0
    avg = float(turnout.mean())
    # normalise if values appear to be 0-100
    return avg / 100.0 if avg > 1 else avg


def _approval_probability(df: pd.DataFrame) -> float:
    """Compute proportion of referenda with status 'executed'."""
    status = df.get("Status")
    if status is None:
        return 0.0
    status = status.astype(str).str.lower()
    return float((status == "executed").mean())


def forecast_outcome(context: Dict[str, Any]) -> Dict[str, float]:
    """Predict approval probability and voter turnout for a proposal.

    Parameters
    ----------
    context : dict
        Current pipeline context (unused but kept for future feature usage).

    Returns
    -------
    dict
        ``{"approval_probability": float, "turnout": float}`` – values are in
        the 0-1 range.
    """
    try:
        df = load_first_sheet()
        approval = _approval_probability(df)
        turnout = _mean_turnout(df)
    except Exception:
        # Fallback heuristics if historical data is unavailable
        approval = 0.5
        turnout = 0.3

    return {
        "approval_probability": round(float(approval), 3),
        "turnout": round(float(turnout), 3),
    }


if __name__ == "__main__":
    print(forecast_outcome({}))
