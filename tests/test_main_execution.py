import src.main as main


def test_main_records_final_status(monkeypatch, tmp_path):
    monkeypatch.setattr(main, "collect_recent_messages", lambda: [])
    monkeypatch.setattr(main, "analyse_messages", lambda msgs: {})
    monkeypatch.setattr(main, "fetch_and_summarise_news", lambda: {})
    monkeypatch.setattr(main, "get_recent_blocks_cached", lambda: [])
    monkeypatch.setattr(main, "summarise_blocks", lambda blocks: {})
    monkeypatch.setattr(main, "update_referenda", lambda max_new: None)
    monkeypatch.setattr(main, "get_governance_insights", lambda as_narrative=True: {})
    monkeypatch.setattr(main, "build_context", lambda *args: {})
    monkeypatch.setattr(main, "forecast_outcomes", lambda context: {})
    monkeypatch.setattr(main, "generate_completion", lambda **kwargs: "Proposal")
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
