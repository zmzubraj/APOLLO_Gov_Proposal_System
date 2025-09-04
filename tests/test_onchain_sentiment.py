import types, sys


def test_onchain_sentiment_included(monkeypatch, tmp_path):
    pandas_module = types.ModuleType("pandas")
    pandas_module.DataFrame = type("DataFrame", (), {})
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

    import src.main as main

    monkeypatch.setattr(main, "collect_recent_messages", lambda: {})
    monkeypatch.setattr(main, "analyse_messages", lambda msgs: {"sentiment": "Neutral", "confidence": 0.5})
    monkeypatch.setattr(main, "fetch_and_summarise_news", lambda: {})
    monkeypatch.setattr(main, "get_recent_blocks_cached", lambda: [{"block_timestamp": 0, "extrinsics_count": 0, "total_fee": 0}])
    monkeypatch.setattr(main, "update_referenda", lambda max_new: None)
    monkeypatch.setattr(main, "get_governance_insights", lambda as_narrative=True: {})
    monkeypatch.setattr(main, "build_context", lambda *a, **k: {})
    monkeypatch.setattr(main, "forecast_outcomes", lambda ctx: {})
    monkeypatch.setattr(main, "compare_predictions", lambda df: {"prediction_eval": []})
    monkeypatch.setattr(main, "evaluate_historical_predictions", lambda: [])
    monkeypatch.setattr(main.proposal_generator, "draft", lambda ctx: "Proposal")
    monkeypatch.setattr(main, "broadcast_proposal", lambda text: None)
    monkeypatch.setattr(
        main, "record_proposal", lambda text, sid, stage=None, **_: None
    )
    monkeypatch.setattr(main, "record_execution_result", lambda *a, **k: None)
    monkeypatch.setattr(main, "print_data_sources_table", lambda stats: None)
    monkeypatch.setattr(main, "print_prediction_accuracy_table", lambda stats: None)
    monkeypatch.setattr(main, "print_timing_benchmarks_table", lambda stats: None)
    monkeypatch.setattr(main.ollama_api, "embed_text", lambda text: [0.0])

    captured = {}

    def fake_print_sentiment_table(batches):
        captured["batches"] = list(batches)

    monkeypatch.setattr(main, "print_sentiment_embedding_table", fake_print_sentiment_table)
    monkeypatch.setattr(main, "OUT_DIR", tmp_path)

    main.main()

    batches = captured.get("batches", [])
    assert any(b.get("source") == "onchain" for b in batches)
    assert all(b.get("source") != "evm_chain" for b in batches)
