import pytest

from agents.data_collector import DataCollector


def test_trending_topics_include_news_and_weights():
    messages = {
        "chat": ["Polkadot upgrades are awesome", "Polkadot community grows"],
    }
    news = {
        "articles": [
            {
                "title": "Polkadot upgrades on track",
                "body": "Community grows rapidly",
                "likes": 10,
                "comments": 5,
            }
        ]
    }

    data = DataCollector.collect(
        msg_fn=lambda: messages, news_fn=lambda: news, block_fn=lambda: []
    )

    trending = data["trending_topics"]
    weights = data["stats"]["trending_topics"]

    assert "polkadot upgrades" in trending
    assert weights["polkadot upgrades"] == pytest.approx(17.0)


def test_html_noise_dropped_from_trending():
    messages = {
        "chat": [
            "<div>style element node style element</div>",
            "<p>style element node style element</p>",
        ]
    }

    data = DataCollector.collect(
        msg_fn=lambda: messages, news_fn=lambda: {}, block_fn=lambda: []
    )

    assert data["trending_topics"] == []
    assert data["stats"]["trending_topics"] == {}


def test_valid_topic_survives_html_noise():
    messages = {
        "chat": [
            "<div>Polkadot upgrade style element</div>",
            "<p>Polkadot upgrade node style element</p>",
        ]
    }

    data = DataCollector.collect(
        msg_fn=lambda: messages, news_fn=lambda: {}, block_fn=lambda: []
    )

    trending = data["trending_topics"]
    weights = data["stats"]["trending_topics"]

    assert trending == ["polkadot upgrade"]
    assert weights["polkadot upgrade"] == pytest.approx(2.0)
