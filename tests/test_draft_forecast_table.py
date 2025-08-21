import importlib

from src import main
from src.reporting.summary_tables import (
    print_draft_forecast_table,
    summarise_draft_predictions,
    load_persisted_draft_predictions,
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
    assert "Forum" in out and "Onchain" in out and "Chat" not in out
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


def test_load_persisted_draft_predictions(monkeypatch):
    import pandas as pd

    df = pd.DataFrame([
        {"proposal_text": "# Title\nBody", "stage": "draft"},
        {"proposal_text": "Other", "stage": "final"},
    ])
    import src.reporting.summary_tables as st

    monkeypatch.setattr(st, "load_proposals", lambda: df)
    monkeypatch.setattr(
        st,
        "forecast_outcomes",
        lambda ctx: {"approval_prob": 0.25, "turnout_estimate": 0.1},
    )
    records = load_persisted_draft_predictions(0.55)
    assert records and records[0]["predicted"] == "Fail"


def test_main_generates_fallback_predictions(monkeypatch, capsys):
    monkeypatch.setenv("MIN_PASS_CONFIDENCE", "0.55")
    importlib.reload(main)

    def dummy_collect(*args, stats=None, **kwargs):
        if stats is not None:
            stats.setdefault("data_sources", {})
        return {"messages": {}, "news": {}, "blocks": [], "stats": stats}

    monkeypatch.setattr(main.DataCollector, "collect", staticmethod(dummy_collect))
    monkeypatch.setattr(main, "analyse_messages", lambda msgs: {})
    monkeypatch.setattr(main, "summarise_blocks", lambda blocks: {})
    monkeypatch.setattr(main, "update_referenda", lambda max_new=1500: None)
    monkeypatch.setattr(main, "get_governance_insights", lambda as_narrative=True: {})
    monkeypatch.setattr(main, "build_context", lambda *args, **kwargs: {})
    monkeypatch.setattr(main.proposal_generator, "draft", lambda ctx: "# Title\nBody")
    monkeypatch.setattr(
        main,
        "forecast_outcomes",
        lambda ctx: {"approval_prob": 0.4, "turnout_estimate": 0.02},
    )
    monkeypatch.setattr(main.ollama_api, "embed_text", lambda text: None)
    monkeypatch.setattr(
        main,
        "compare_predictions",
        lambda df_pred, df_actual=None: {"prediction_eval": []},
    )
    monkeypatch.setattr(main, "evaluate_historical_predictions", lambda sample_size=5: [])
    monkeypatch.setattr(main, "broadcast_proposal", lambda text: None)
    import pandas as pd
    import src.reporting.summary_tables as st

    df = pd.DataFrame([
        {"proposal_text": "# Title\nBody", "stage": "draft"}
    ])
    monkeypatch.setattr(st, "load_proposals", lambda: df)
    monkeypatch.setattr(
        st,
        "forecast_outcomes",
        lambda ctx: {"approval_prob": 0.4, "turnout_estimate": 0.02},
    )
    monkeypatch.setattr(main, "record_proposal", lambda *args, **kwargs: None)
    monkeypatch.setattr(main, "record_execution_result", lambda **kwargs: None)

    main.main()
    out = capsys.readouterr().out
    assert "Draft proposals:" in out
    assert "Source: consolidated" in out
    assert "Table: Drafted proposal success prediction and forecast" in out
    assert "No draft predictions available" not in out
