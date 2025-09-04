import json
from pathlib import Path

from src.agents.outcome_forecaster import forecast_outcomes
from src.data_processing import referenda_updater


def test_probability_varies_with_sentiment(monkeypatch):
    monkeypatch.setattr(
        referenda_updater,
        "load_historical_rates",
        lambda: {"approval_rate": 0.5, "turnout": 0.5, "turnout_trend": 0.0},
    )
    low = forecast_outcomes({"source_sentiments": {"chat": -0.5}})["approval_prob"]
    high = forecast_outcomes({"source_sentiments": {"chat": 0.5}})["approval_prob"]
    assert high > low


def test_probability_varies_with_comment_trend(monkeypatch):
    monkeypatch.setattr(
        referenda_updater,
        "load_historical_rates",
        lambda: {"approval_rate": 0.5, "turnout": 0.5, "turnout_trend": 0.0},
    )
    low = forecast_outcomes({"comment_turnout_trend": -0.2})["approval_prob"]
    high = forecast_outcomes({"comment_turnout_trend": 0.2})["approval_prob"]

    model_path = Path(__file__).resolve().parents[1] / "models" / "referendum_model.json"
    with model_path.open() as f:
        coeff = json.load(f)["coefficients"].get("comment_turnout_trend", 0.0)
    if coeff >= 0:
        assert high > low
    else:
        assert high < low
