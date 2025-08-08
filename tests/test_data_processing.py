import pandas as pd
from data_processing import proposal_store


def test_search_proposals_returns_matches(monkeypatch):
    df = pd.DataFrame(
        [
            {"proposal_text": "Improve governance transparency"},
            {"proposal_text": "Another proposal about fees"},
        ]
    )
    monkeypatch.setattr(proposal_store, "load_proposals", lambda: df)

    results = proposal_store.search_proposals("governance", limit=5)
    assert results == ["Improve governance transparency"]

