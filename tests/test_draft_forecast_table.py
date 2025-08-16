import importlib

from src import main


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
