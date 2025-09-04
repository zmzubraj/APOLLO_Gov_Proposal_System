import json
from pathlib import Path

import numpy as np

from src.agents.outcome_forecaster import forecast_outcomes
from src.data_processing import referenda_updater


def test_forecast_outcomes_fields_and_ranges(tmp_path, monkeypatch):
    monkeypatch.setattr(
        referenda_updater,
        "load_historical_rates",
        lambda: {"approval_rate": 0.5, "turnout": 0.5, "turnout_trend": 0.02},
    )

    context = {
        "sentiment_score": 0.2,
        "trending_score": 0.1,
        "source_sentiments": {"news": 0.3, "forum": 0.1},
        "comment_turnout_trend": 0.05,
    }
    result = forecast_outcomes(context)
    assert set(result.keys()) == {"approval_prob", "turnout_estimate"}
    assert 0.0 <= result["approval_prob"] <= 1.0
    assert 0.0 <= result["turnout_estimate"] <= 1.0

    model_path = Path(__file__).resolve().parents[1] / "models" / "referendum_model.json"
    with model_path.open() as f:
        model = json.load(f)
    coeffs = model["coefficients"]
    z = (
        model["intercept"]
        + coeffs.get("approval_rate", 0.0) * 0.5
        + coeffs.get("turnout", 0.0) * 0.5
        + coeffs.get("sentiment", 0.0) * 0.2
        + coeffs.get("trending", 0.0) * 0.1
        + coeffs.get("source_sentiment_avg", 0.0) * 0.2
        + coeffs.get("comment_turnout_trend", 0.0) * 0.05
    )
    expected = 1 / (1 + np.exp(-z))
    assert round(result["approval_prob"], 3) == round(expected, 3)
    assert round(result["turnout_estimate"], 2) == 0.5


def test_probability_increases_with_sentiment(monkeypatch):
    monkeypatch.setattr(
        referenda_updater,
        "load_historical_rates",
        lambda: {"approval_rate": 0.5, "turnout": 0.5, "turnout_trend": 0.0},
    )

    ctx_low = {"source_sentiments": {"news": -0.5}}
    ctx_high = {"source_sentiments": {"news": 0.5}}
    low = forecast_outcomes(ctx_low)["approval_prob"]
    high = forecast_outcomes(ctx_high)["approval_prob"]
    assert high > low
