"""
pytest smoke tests – run `pytest -q`
They skip external API calls by mocking the modules,
so the tests are fast and deterministic.
"""

from src.utils import validators as v
from data_processing import proposal_store
from src.agents.context_generator import build_context
from llm import ollama_api


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


def test_stored_proposals_influence_context(tmp_path, monkeypatch):
    """Proposals saved to the store should surface in later contexts."""

    tmp_xlsx = tmp_path / "test_store.xlsx"
    monkeypatch.setattr(proposal_store, "XLSX_PATH", tmp_xlsx)

    # Simulate a previous run recording proposal and context
    proposal_store.record_proposal("Increase staking rewards", submission_id=None)
    proposal_store.record_context({"note": "staking yields high"})

    # Patch embeddings so "staking" aligns with the stored proposal
    def fake_embed(text: str):
        return [1, 0] if "staking" in text.lower() else [0, 1]

    monkeypatch.setattr(ollama_api, "embed_text", fake_embed)
    monkeypatch.setattr(proposal_store, "record_context", lambda _c: None)

    ctx = build_context({}, {}, {}, {}, kb_query="staking")
    assert any("Increase staking rewards" in s for s in ctx["kb_snippets"])
