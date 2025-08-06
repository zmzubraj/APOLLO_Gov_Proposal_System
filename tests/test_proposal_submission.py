from src.agents.proposal_submission import submit_proposal


def test_submit_proposal_http(monkeypatch):
    """Snapshot-style HTTP submission returns identifier."""
    def fake_post(url, json=None, headers=None, timeout=10):
        assert url == "https://snapshot.fake/api"
        assert json["proposal"] == "hello"
        assert headers["Authorization"] == "Bearer key"
        class Resp:
            def raise_for_status(self):
                pass
            def json(self):
                return {"url": "https://snapshot.fake/p/1"}
        return Resp()
    monkeypatch.setattr("requests.post", fake_post)
    creds = {"api_url": "https://snapshot.fake/api", "api_key": "key"}
    res = submit_proposal("hello", creds)
    assert res == "https://snapshot.fake/p/1"


def test_submit_proposal_env(monkeypatch):
    """Environment variables supply credentials when none passed."""
    def fake_post(url, json=None, headers=None, timeout=10):
        assert url == "https://snapshot.fake/api"
        assert json["proposal"] == "hi"
        assert headers["Authorization"] == "Bearer key"
        class Resp:
            def raise_for_status(self):
                pass
            def json(self):
                return {"url": "https://snapshot.fake/p/2"}
        return Resp()
    monkeypatch.setattr("requests.post", fake_post)
    monkeypatch.setenv("PROPOSAL_PLATFORM", "snapshot")
    monkeypatch.setenv("SNAPSHOT_API_URL", "https://snapshot.fake/api")
    monkeypatch.setenv("SNAPSHOT_API_KEY", "key")
    res = submit_proposal("hi")
    assert res == "https://snapshot.fake/p/2"


def test_main_submits(monkeypatch, capsys):
    """Pipeline integrates submission step."""
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
    monkeypatch.setattr(main, "update_referenda", lambda max_new=500: None)
    monkeypatch.setattr(main, "get_recent_blocks_cached", lambda: [])
    monkeypatch.setattr(main, "summarise_blocks", lambda blocks: {})
    monkeypatch.setattr(main, "get_governance_insights", lambda as_narrative=True: {})
    monkeypatch.setattr(main, "generate_completion", lambda **kwargs: "proposal text")

    def fake_submit(text, credentials=None):
        assert text == "proposal text"
        return "abc123"
    monkeypatch.setattr(main, "submit_proposal", fake_submit)

    main.main()
    out = capsys.readouterr().out
    assert "abc123" in out
