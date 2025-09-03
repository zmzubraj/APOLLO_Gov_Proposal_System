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
