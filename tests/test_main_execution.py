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

    monkeypatch.setattr(main, "collect_recent_messages", lambda: {})
    monkeypatch.setattr(main, "analyse_messages", lambda msgs: {})
    monkeypatch.setattr(main, "fetch_and_summarise_news", lambda: {})
    monkeypatch.setattr(main, "get_recent_blocks_cached", lambda: [])
    monkeypatch.setattr(main, "summarise_blocks", lambda blocks: {})
    monkeypatch.setattr(main, "update_referenda", lambda max_new: None)
    monkeypatch.setattr(main, "get_governance_insights", lambda as_narrative=True: {})
    captured_kb = {}

    def fake_build_context(sentiment, news, chain, gov, evm=None, kb_snippets=None, kb_query=None, **_):
        captured_kb["query"] = kb_query
        return {}

    monkeypatch.setattr(main, "build_context", fake_build_context)
    monkeypatch.setattr(main, "forecast_outcomes", lambda context: {})
    monkeypatch.setattr(main.proposal_generator, "draft", lambda context: "Proposal")
    monkeypatch.setattr(main, "broadcast_proposal", lambda text: None)
    monkeypatch.setattr(
        main,
        "submit_preimage",
        lambda url, pk, data: {"preimage_hash": "0xhash", "extrinsic_hash": "0xpre"},
    )
    monkeypatch.setattr(
        main,
        "submit_proposal",
        lambda url, pk, hash_, track: {
            "extrinsic_hash": "0xsub",
            "referendum_index": 1,
            "is_success": True,
        },
    )
    monkeypatch.setattr(
        main, "record_proposal", lambda text, sid, stage=None, **_: None
    )
    monkeypatch.setattr(main, "await_execution", lambda node_url, idx, sid: ("0xblock", "Approved"))
    monkeypatch.setattr(
        main,
        "execute_proposal",
        lambda url, pk: {"extrinsic_hash": "0xexec", "block_hash": "0xexecblock"},
    )

    recorded = {}

    def fake_record_execution_result(
        status,
        block_hash,
        outcome,
        submission_id=None,
        extrinsic_hash=None,
        referendum_index=None,
    ):
        recorded.update(
            status=status,
            block_hash=block_hash,
            outcome=outcome,
            submission_id=submission_id,
            extrinsic_hash=extrinsic_hash,
            referendum_index=referendum_index,
        )

    monkeypatch.setattr(main, "record_execution_result", fake_record_execution_result)

    monkeypatch.setattr(main, "OUT_DIR", tmp_path)
    monkeypatch.setenv("SUBSTRATE_NODE_URL", "ws://node")
    monkeypatch.setenv("SUBSTRATE_PRIVATE_KEY", "priv")
    monkeypatch.setenv("GOVERNANCE_TRACK", "root")

    main.main()

    assert recorded == {
        "status": "Executed",
        "block_hash": "0xexecblock",
        "outcome": "Approved",
        "submission_id": "0xsub",
        "extrinsic_hash": "0xexec",
        "referendum_index": 1,
    }
    assert captured_kb["query"] == ""
