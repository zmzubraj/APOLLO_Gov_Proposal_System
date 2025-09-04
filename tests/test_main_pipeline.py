import types
import sys
import importlib
import types
import json
import pytest


@pytest.fixture
def main_module():
    """Import src.main with heavy dependencies stubbed."""
    pandas_module = types.ModuleType("pandas")
    pandas_module.DataFrame = lambda *a, **k: {}
    pandas_module.read_excel = lambda *a, **k: pandas_module.DataFrame()
    sys.modules.setdefault("pandas", pandas_module)

    bs4_module = types.ModuleType("bs4")
    bs4_module.BeautifulSoup = object
    sys.modules.setdefault("bs4", bs4_module)

    feedparser_module = types.ModuleType("feedparser")
    feedparser_module.parse = lambda *a, **k: types.SimpleNamespace(entries=[])
    sys.modules.setdefault("feedparser", feedparser_module)

    numpy_module = types.ModuleType("numpy")
    sys.modules.setdefault("numpy", numpy_module)

    substrate_module = types.ModuleType("substrateinterface")
    substrate_module.SubstrateInterface = object
    sys.modules.setdefault("substrateinterface", substrate_module)

    dotenv_module = types.ModuleType("dotenv")
    dotenv_module.load_dotenv = lambda *a, **k: None
    sys.modules.setdefault("dotenv", dotenv_module)

    import src.main as main
    importlib.reload(main)
    return main


@pytest.mark.parametrize(
    "empty_fetcher, skipped_source",
    [
        ("collect_recent_messages", "forum"),
        ("fetch_and_summarise_news", "news"),
        ("get_recent_blocks_cached", "onchain"),
    ],
)
def test_pipeline_skips_empty_source(empty_fetcher, skipped_source, monkeypatch, tmp_path, main_module):
    main = main_module

    # --- basic stubs for external interactions ---
    monkeypatch.setattr(main.ollama_api, "check_server", lambda: None)
    monkeypatch.setattr(main.ollama_api, "embed_text", lambda text: None)
    monkeypatch.setattr(main, "analyse_messages", lambda msgs: {"sentiment": "Neutral", "confidence": 1, "message_size_kb": 1})
    monkeypatch.setattr(main, "forecast_outcomes", lambda ctx: {"approval_prob": 0.9})
    monkeypatch.setattr(main, "build_context", lambda *a, **k: {})
    monkeypatch.setattr(main, "update_referenda", lambda max_new: None)
    monkeypatch.setattr(main, "get_governance_insights", lambda as_narrative=True: {})
    monkeypatch.setattr(main, "draft_onchain_proposal", lambda *a, **k: None)
    monkeypatch.setattr(main.proposal_generator, "draft", lambda ctx, **kw: "draft")
    monkeypatch.setattr(main, "compare_predictions", lambda df: {"prediction_eval": []})
    monkeypatch.setattr(main, "evaluate_historical_predictions", lambda: [])
    monkeypatch.setattr(main, "broadcast_proposal", lambda text: None)
    monkeypatch.setattr(main, "print_data_sources_table", lambda *a, **k: None)
    monkeypatch.setattr(main, "print_sentiment_embedding_table", lambda *a, **k: None)
    monkeypatch.setattr(main, "print_draft_forecast_table", lambda *a, **k: None)
    monkeypatch.setattr(main, "print_prediction_accuracy_table", lambda *a, **k: None)
    monkeypatch.setattr(main, "print_timing_benchmarks_table", lambda *a, **k: None)
    monkeypatch.setattr(main, "record_execution_result", lambda *a, **k: None)

    recorded_sources = []

    def fake_record_proposal(text, submission_id, stage=None, source=None, **_):
        if stage == "draft":
            recorded_sources.append(source)

    monkeypatch.setattr(main, "record_proposal", fake_record_proposal)
    monkeypatch.setattr(main, "OUT_DIR", tmp_path)

    # Default fetcher outputs
    def msg_data():
        return {"forum": ["hi there"]}

    def news_data():
        return {"articles": [{"title": "t", "body": "b"}]}

    def block_data():
        return [{"block_timestamp": 0, "extrinsics_count": 1}]

    monkeypatch.setattr(main, "collect_recent_messages", msg_data)
    monkeypatch.setattr(main, "fetch_and_summarise_news", news_data)
    monkeypatch.setattr(main, "get_recent_blocks_cached", block_data)

    # Specific fetcher returns empty
    if empty_fetcher == "collect_recent_messages":
        monkeypatch.setattr(main, "collect_recent_messages", lambda: {})
    elif empty_fetcher == "fetch_and_summarise_news":
        monkeypatch.setattr(main, "fetch_and_summarise_news", lambda: {})
    elif empty_fetcher == "get_recent_blocks_cached":
        monkeypatch.setattr(main, "get_recent_blocks_cached", lambda: [])

    main.main()

    # Ensure the draft JSON includes the full context
    draft_files = list(tmp_path.glob("draft_*.json"))
    assert draft_files, "No draft artifact generated"
    payload = json.loads(draft_files[0].read_text())
    assert "context" in payload

    assert skipped_source not in recorded_sources
    # At least one proposal draft should exist from remaining data
    assert recorded_sources
