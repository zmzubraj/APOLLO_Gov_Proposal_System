import json
from pathlib import Path

from src.agents import outcome_forecaster
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


def test_fallback_forecast_uses_context(monkeypatch):
    monkeypatch.setattr(
        referenda_updater,
        "load_historical_rates",
        lambda: {"approval_rate": 0.5, "turnout": 0.5, "turnout_trend": 0.0},
    )
    monkeypatch.setattr(outcome_forecaster, "_load_model", lambda: None)

    ctx_negative = {"sentiment_score": -0.4, "comment_turnout_trend": -0.3}
    ctx_positive = {"sentiment_score": 0.4, "comment_turnout_trend": 0.3}

    low = forecast_outcomes(ctx_negative)["approval_prob"]
    high = forecast_outcomes(ctx_positive)["approval_prob"]
    assert high > low


def test_margin_and_confidence_reflect_context(monkeypatch):
    monkeypatch.setattr(
        referenda_updater,
        "load_historical_rates",
        lambda: {"approval_rate": 0.5, "turnout": 0.5, "turnout_trend": 0.05},
    )
    monkeypatch.setattr(outcome_forecaster, "_load_model", lambda: None)

    calm_context = {
        "source_sentiments": {"news": 0.1, "forum": 0.15},
        "comment_turnout_trend": 0.02,
        "engagement_weight": 0.9,
    }
    volatile_context = {
        "source_sentiments": {"news": -0.4, "forum": 0.45},
        "comment_turnout_trend": 0.25,
        "engagement_weight": 0.1,
    }

    calm_result = forecast_outcomes(calm_context)
    volatile_result = forecast_outcomes(volatile_context)

    assert volatile_result["margin_of_error"] > calm_result["margin_of_error"]
    assert volatile_result["confidence"] < calm_result["confidence"]
