"""Compatibility wrapper for prediction analysis functions."""
from __future__ import annotations

from typing import Dict

from agents.outcome_forecaster import forecast_outcomes as _forecast_outcomes

__all__ = ["forecast_outcomes"]


def forecast_outcomes(context: Dict) -> Dict[str, float]:
    """Delegate to :func:`agents.outcome_forecaster.forecast_outcomes`."""
    return _forecast_outcomes(context)
