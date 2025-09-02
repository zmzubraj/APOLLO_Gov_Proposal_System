import pytest
from data_processing import social_media_scraper as scraper

def test_collect_recent_messages_grouped_and_dedup(monkeypatch):
    monkeypatch.setattr(scraper, "fetch_x", lambda: ["hello", "dup"])
    monkeypatch.setattr(scraper, "fetch_reddit", lambda limit=20: ["dup", "world"])

    forum_topics = [
        {"title": "Topic1", "details": {}, "comments_replies": []},
        {"title": "Topic1", "details": {}, "comments_replies": []},
        {"title": "Topic2", "details": {}, "comments_replies": []},
    ]
    monkeypatch.setattr(scraper, "fetch_forum", lambda limit=15: forum_topics)

    monkeypatch.setattr(scraper, "fetch_cryptorank", lambda: ["n1", "dup"])
    monkeypatch.setattr(scraper, "fetch_binance_square", lambda limit=30: ["dup", "n2"])

    grouped = scraper.collect_recent_messages()

    assert set(grouped) == {"chat", "forum", "news"}

    chat = grouped["chat"]
    assert isinstance(chat, list)
    assert chat == ["hello", "dup", "world"]
    assert all(isinstance(item, str) for item in chat)

    forum = grouped["forum"]
    assert isinstance(forum, list)
    assert [t["title"] for t in forum] == ["Topic1", "Topic2"]
    assert all(isinstance(item, dict) for item in forum)

    news = grouped["news"]
    assert isinstance(news, list)
    assert news == ["n1", "dup", "n2"]
    assert all(isinstance(item, str) for item in news)

    # ensure duplicates removed
    assert len(set(chat)) == len(chat)
    assert len({t["title"] for t in forum}) == len(forum)
    assert len(set(news)) == len(news)
