import pandas as pd

from agents.data_collector import DataCollector
from agents import data_collector


def test_governance_stats(monkeypatch, tmp_path):
    df = pd.DataFrame({"a": ["hello world", "foo bar"]})
    fake_path = tmp_path / "dummy.xlsx"
    fake_path.touch()
    monkeypatch.setattr(data_collector, "ROOT", tmp_path)
    monkeypatch.setattr(data_collector, "XLSX_PATH", fake_path)
    monkeypatch.setattr(data_collector.pd, "read_excel", lambda *args, **kwargs: {"Context": df})
    data = DataCollector.collect(msg_fn=lambda: {}, news_fn=lambda: {}, block_fn=lambda: [])
    gov = data["stats"]["data_sources"]["governance"]
    assert gov["count"] == 2
    assert gov["avg_word_length"] == 2.0
    assert gov["total_tokens"] == 4
