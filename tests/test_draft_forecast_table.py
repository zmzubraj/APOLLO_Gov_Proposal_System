import importlib

from src import main
from src.reporting.summary_tables import print_draft_forecast_table


def test_drafts_under_threshold_label_fail(monkeypatch):
    monkeypatch.setenv("MIN_PASS_CONFIDENCE", "0.9")
    importlib.reload(main)
    drafts = [
        {
            "source": "chat",
            "text": "# Title\nBody",
            "forecast": {"approval_prob": 0.5, "turnout_estimate": 0.1},
            "prediction_time": 0.01,
        }
    ]
    records = main.summarise_draft_predictions(drafts, main.MIN_PASS_CONFIDENCE)
    assert records[0]["predicted"] == "Fail"


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
    ]
    print_draft_forecast_table(stats, 0.8)
    out = capsys.readouterr().out
    assert "Drafted proposal success prediction and forecast" in out
    assert "Pass confidence threshold <80%" in out
    assert "Forum" in out and "Chat" not in out
    assert "79%" in out
    assert "±3%" in out
