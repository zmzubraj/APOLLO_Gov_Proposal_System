import datetime as dt

import pytest

from analysis import blockchain_metrics, news_analysis


def test_summarise_blocks_empty_returns_defaults():
    assert blockchain_metrics.summarise_blocks([]) == {
        "daily_tx_count": {},
        "daily_total_fees_DOT": {},
        "avg_tx_per_block": 0,
        "avg_fee_per_tx_DOT": 0,
        "busiest_hour_utc": "",
    }


def test_summarise_blocks_computes_metrics():
    base = dt.datetime(2024, 1, 1, tzinfo=dt.UTC)
    blocks = [
        {
            "block_timestamp": int(base.timestamp()),
            "extrinsics_count": 10,
            "total_fee": 2 * 10**10,
        },
        {
            "block_timestamp": int((base + dt.timedelta(hours=1)).timestamp()),
            "extrinsics_count": 20,
            "total_fee": 4 * 10**10,
        },
        {
            "block_timestamp": int((base + dt.timedelta(days=1)).timestamp()),
            "extrinsics_count": 5,
            "total_fee": 1 * 10**10,
        },
    ]
    result = blockchain_metrics.summarise_blocks(blocks)
    assert result["daily_tx_count"] == {"2024-01-01": 30, "2024-01-02": 5}
    assert result["daily_total_fees_DOT"] == {"2024-01-01": 6.0, "2024-01-02": 1.0}
    assert result["avg_tx_per_block"] == pytest.approx(11.67, rel=1e-2)
    assert result["avg_fee_per_tx_DOT"] == pytest.approx(0.2, rel=1e-6)
    assert result["busiest_hour_utc"] == "2024-01-01 01:00"


def test_summarise_evm_blocks():
    base = dt.datetime(2024, 1, 1, tzinfo=dt.UTC)
    blocks = [
        {
            "timestamp": int(base.timestamp()),
            "transactions": [
                {"value": 2 * 10**18},
                {"value": 1 * 10**18},
            ],
        },
        {
            "timestamp": int((base + dt.timedelta(hours=1)).timestamp()),
            "transactions": [{"value": 0}],
        },
        {
            "timestamp": int((base + dt.timedelta(days=1)).timestamp()),
            "transactions": [{"value": 5 * 10**17}],
        },
    ]
    res = blockchain_metrics.summarise_evm_blocks(blocks)
    assert res["daily_tx_count"] == {"2024-01-01": 3, "2024-01-02": 1}
    assert res["daily_total_value_ETH"] == {"2024-01-01": 3.0, "2024-01-02": 0.5}
    assert res["avg_tx_per_block"] == pytest.approx(1.33, rel=1e-2)
    assert res["avg_value_per_tx_ETH"] == pytest.approx(0.875, rel=1e-6)


def test_summarise_news_handles_empty():
    assert news_analysis.summarise_news([]) == {
        "digest": [],
        "risks": "No recent Polkadot news in the last 3 days.",
    }


def test_summarise_news_parses_llm_output(monkeypatch):
    called = {}

    def fake_generate(prompt, system, temperature, max_tokens, model):
        called["prompt"] = prompt
        called["system"] = system
        return '{"digest":["one"],"risks":"two"}'

    monkeypatch.setattr(news_analysis, "generate_completion", fake_generate)

    items = [{"title": "T1", "summary": "S1"}]
    result = news_analysis.summarise_news(items)

    assert result == {"digest": ["one"], "risks": "two"}
    assert "T1" in called["prompt"] and "S1" in called["prompt"]
    assert called["system"] == news_analysis.SYSTEM_PROMPT
