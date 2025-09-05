import types, sys

def test_selects_highest_approval_prob(monkeypatch, tmp_path):
    # Stub heavy dependencies
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

    monkeypatch.setattr(main, "collect_recent_messages", lambda: {"a": ["m1"], "b": ["m2"]})
    monkeypatch.setattr(main, "analyse_messages", lambda msgs: {})
    monkeypatch.setattr(main, "fetch_and_summarise_news", lambda: {})
    monkeypatch.setattr(main, "get_recent_blocks_cached", lambda: [])
    monkeypatch.setattr(main, "update_referenda", lambda max_new: None)
    monkeypatch.setattr(main, "get_governance_insights", lambda as_narrative=True: {})
    monkeypatch.setattr(main, "compare_predictions", lambda df: {"prediction_eval": []})
    monkeypatch.setattr(main, "evaluate_historical_predictions", lambda: [])

    contexts = []

    def fake_build_context(*args, **kwargs):
        ctx = {"id": len(contexts)}
        contexts.append(ctx)
        return ctx

    monkeypatch.setattr(main, "build_context", fake_build_context)
    import src.reporting.summary_tables as summary_tables
    monkeypatch.setattr(summary_tables, "build_context", fake_build_context)
    monkeypatch.setattr(
        summary_tables.proposal_generator,
        "draft",
        lambda ctx, source_name: f"Proposal {ctx.get('id', 0)}",
    )

    def fake_forecast(ctx):
        prob = 0.1 if ctx["id"] == 0 else 0.9
        return {"approval_prob": prob, "turnout_estimate": 0.0}

    monkeypatch.setattr(main, "forecast_outcomes", fake_forecast)
    monkeypatch.setattr(
        main.proposal_generator,
        "draft",
        lambda ctx, source_name: f"Proposal {ctx.get('id', 0)}",
    )
    monkeypatch.setattr(main, "broadcast_proposal", lambda text: None)
    monkeypatch.setattr(main, "submit_preimage", lambda url, pk, data: {"preimage_hash": "0xpre"})
    monkeypatch.setattr(main, "submit_proposal", lambda url, pk, h, track: {"extrinsic_hash": "0xsub", "referendum_index": 1, "is_success": True})
    monkeypatch.setattr(main, "await_execution", lambda url, idx, sid: ("0xblock", "Approved"))
    monkeypatch.setattr(main, "execute_proposal", lambda url, pk: {"extrinsic_hash": "0xexec", "block_hash": "0xblock"})
    monkeypatch.setattr(main, "record_execution_result", lambda **kwargs: None)

    # Avoid network calls to the local Ollama server
    monkeypatch.setattr(main.ollama_api, "check_server", lambda: None)

    records = []

    def fake_record_proposal(text, sid, stage=None, **kwargs):
        records.append((text, sid, stage))

    monkeypatch.setattr(main, "record_proposal", fake_record_proposal)

    monkeypatch.setattr(main, "OUT_DIR", tmp_path)
    monkeypatch.setenv("SUBSTRATE_NODE_URL", "ws://node")
    monkeypatch.setenv("SUBSTRATE_PRIVATE_KEY", "priv")
    monkeypatch.setenv("GOVERNANCE_TRACK", "root")

    main.main()

    assert ("Proposal 1", "0xsub", "submitted") in records
