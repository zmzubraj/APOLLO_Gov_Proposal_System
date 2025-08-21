import importlib

from src import main
from src.reporting.summary_tables import (
    print_draft_forecast_table,
    summarise_draft_predictions,
)


def test_drafts_under_threshold_label_fail(monkeypatch):
    monkeypatch.setenv("MIN_PASS_CONFIDENCE", "0.9")
    importlib.reload(main)
    drafts = [
        {
            "source": "chat",
            "text": "# Title\nBody",
            "forecast": {"approval_prob": 0.2, "turnout_estimate": 0.1},
            "prediction_time": 0.01,
        }
    ]
    records = summarise_draft_predictions(drafts, main.MIN_PASS_CONFIDENCE)
    assert records[0]["predicted"] == "Fail"
    assert abs(records[0]["confidence"] - 0.8) < 1e-9


def test_print_draft_forecast_table_output(capsys):
    stats = [
        {
            "source": "forum",
            "title": "a",
            "predicted": "Pass",
            "confidence": 0.79,
            "prediction_time": 5.3,
            "margin_of_error": 0.03,
        },
        {
            "source": "chat",
            "title": "b",
            "predicted": "Pass",
            "confidence": 0.89,
            "prediction_time": 4.2,
            "margin_of_error": 0.05,
        },
        {
            "source": "onchain",
            "title": "c",
            "predicted": "Fail",
            "confidence": 0.74,
            "prediction_time": 3.1,
            "margin_of_error": 0.07,
        },
    ]
    print_draft_forecast_table(stats, 0.8)
    out = capsys.readouterr().out
    assert "Drafted proposal success prediction and forecast" in out
    assert "Pass confidence threshold <80%" in out
    assert "Forum" in out and "Onchain" in out and "Chat" in out
    assert "79%" in out
    assert "±3%" in out


def test_print_draft_forecast_table_includes_fail_high_confidence(capsys):
    stats = [
        {
            "source": "forum",
            "title": "a",
            "predicted": "Fail",
            "confidence": 0.95,
            "prediction_time": 1.0,
            "margin_of_error": 0.02,
        }
    ]
    print_draft_forecast_table(stats, 0.8)
    out = capsys.readouterr().out
    assert "forum".capitalize() in out  # source is shown
    assert "95%" in out


def test_summarise_uses_stored_proposals(monkeypatch):
    import pandas as pd

    df = pd.DataFrame({"proposal_text": ["# Title"], "stage": ["draft"]})
    monkeypatch.setattr(
        "data_processing.proposal_store.load_proposals", lambda: df
    )
    records = summarise_draft_predictions([], 0.5)
    assert records and records[0]["title"] == "Title"
