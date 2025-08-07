def test_main_records_final_status(monkeypatch, tmp_path):
    import types, sys
    # Stub heavy dependencies before importing main
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

    monkeypatch.setattr(main, "collect_recent_messages", lambda: [])
    monkeypatch.setattr(main, "analyse_messages", lambda msgs: {})
    monkeypatch.setattr(main, "fetch_and_summarise_news", lambda: {})
    monkeypatch.setattr(main, "get_recent_blocks_cached", lambda: [])
    monkeypatch.setattr(main, "summarise_blocks", lambda blocks: {})
    monkeypatch.setattr(main, "update_referenda", lambda max_new: None)
    monkeypatch.setattr(main, "get_governance_insights", lambda as_narrative=True: {})
    captured_kb = {}

    def fake_build_context(sentiment, news, chain, gov, kb_snippets=None):
        captured_kb["snippets"] = kb_snippets
        return {}

    monkeypatch.setattr(main, "build_context", fake_build_context)
    monkeypatch.setattr(main, "forecast_outcomes", lambda context: {})
    monkeypatch.setattr(main.proposal_generator, "draft", lambda context: "Proposal")
    monkeypatch.setattr(main, "broadcast_proposal", lambda text: None)
    monkeypatch.setattr(main, "submit_proposal", lambda text: "0xsub")
    monkeypatch.setattr(main, "record_proposal", lambda text, sid: None)
    monkeypatch.setattr(main, "record_context", lambda context: None)
    monkeypatch.setattr(main, "await_execution", lambda node_url, idx, sid: ("0xblock", "Approved"))

    recorded = {}

    def fake_record_execution_result(status, block_hash, outcome, submission_id=None):
        recorded.update(status=status, block_hash=block_hash, outcome=outcome, submission_id=submission_id)

    monkeypatch.setattr(main, "record_execution_result", fake_record_execution_result)

    monkeypatch.setattr(main, "OUT_DIR", tmp_path)
    monkeypatch.setenv("SUBSTRATE_NODE_URL", "ws://node")
    monkeypatch.setenv("REFERENDUM_INDEX", "1")

    main.main()

    assert recorded == {
        "status": "Approved",
        "block_hash": "0xblock",
        "outcome": "Approved",
        "submission_id": "0xsub",
    }
    assert captured_kb["snippets"] == []
