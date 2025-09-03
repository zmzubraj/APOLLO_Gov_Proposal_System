import datetime as dt
import logging

import pytest

from data_processing import news_fetcher


def _make_feed(count: int):
    now = dt.datetime.now(dt.UTC)
    entries = []
    for i in range(count):
        e = type("E", (), {})()
        e.title = f"title-{i}-{count}"
        e.summary = "sum"
        e.published_parsed = now.timetuple()
        entries.append(e)
    return type("F", (), {"entries": entries})()


def test_collect_recent_items_fallback(monkeypatch):
    calls: list[str] = []

    def fake_parse(url):
        calls.append(url)
        if len(calls) <= len(news_fetcher.RSS_FEEDS):
            return _make_feed(5)
        return _make_feed(25)

    monkeypatch.setattr(news_fetcher.feedparser, "parse", fake_parse)

    items = news_fetcher._collect_recent_items()

    assert len(items) >= news_fetcher.MIN_ARTICLES
    assert len(calls) > len(news_fetcher.RSS_FEEDS)


def test_collect_recent_items_warns(monkeypatch, caplog):
    def fake_parse(url):
        return _make_feed(0)

    monkeypatch.setattr(news_fetcher.feedparser, "parse", fake_parse)

    with caplog.at_level(logging.WARNING):
        items = news_fetcher._collect_recent_items()

    assert len(items) == 0
    assert "Only" in caplog.text

