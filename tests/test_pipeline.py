"""
pytest smoke tests – run `pytest -q`
They skip external API calls by mocking the modules,
so the tests are fast and deterministic.
"""

from src.utils import validators as v


def test_validators_pass_on_dummy():
    sent = {
        "sentiment_score": 0.1,
        "summary": "ok",
        "key_topics": [],
    }
    news = {"digest": [], "risks": ""}
    chain = {
        "daily_tx_count": {},
        "daily_total_fees_DOT": {},
        "avg_tx_per_block": 0,
        "avg_fee_per_tx_DOT": 0,
        "busiest_hour_utc": "",
    }
    gov = {
        "total_referenda": 1,
        "executed_pct": 50,
        "rejected_pct": 50,
        "avg_turnout_pct": 1.2,
        "median_turnout_pct": 0.9,
        "avg_participants": 123,
        "avg_duration_days": 8.2,
        "monthly_counts": {},
        "top_keywords": [],
    }
    assert v.validate_sentiment(sent)
    assert v.validate_news(news)
    assert v.validate_chain_kpis(chain)
    assert v.validate_governance_kpis(gov)
