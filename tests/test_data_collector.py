import types, sys

pandas_module = types.ModuleType("pandas")
pandas_module.DataFrame = lambda *a, **k: None
sys.modules.setdefault("pandas", pandas_module)

feedparser_module = types.ModuleType("feedparser")
feedparser_module.parse = lambda *a, **k: types.SimpleNamespace(entries=[])
sys.modules.setdefault("feedparser", feedparser_module)

bs4_module = types.ModuleType("bs4")
bs4_module.BeautifulSoup = object
sys.modules.setdefault("bs4", bs4_module)

substrate_module = types.ModuleType("substrateinterface")
substrate_module.SubstrateInterface = object
sys.modules.setdefault("substrateinterface", substrate_module)

requests_module = types.ModuleType("requests")
requests_module.get = lambda *a, **k: types.SimpleNamespace(json=lambda: {}, raise_for_status=lambda: None)
sys.modules.setdefault("requests", requests_module)

web3_module = types.ModuleType("web3")
web3_module.Web3 = object
sys.modules.setdefault("web3", web3_module)

from agents.data_collector import DataCollector
from analysis.blockchain_metrics import summarise_blocks


def test_collect_skips_empty_sources():
    """DataCollector should drop sources that return no items."""
    messages_fn = lambda: {"chat": [], "forum": ["hello"]}
    news_fn = lambda: {"articles": []}
    blocks_fn = lambda: []

    data = DataCollector.collect(messages_fn, news_fn, blocks_fn)

    # The empty "chat" source should be removed, "forum" retained
    assert "chat" not in data["messages"]
    assert data["messages"] == {"forum": ["hello"]}

    # Empty news and block fetchers should yield empty structures
    assert data["news"] == {}
    expected = summarise_blocks([])
    assert data["blocks"] == expected
