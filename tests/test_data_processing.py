import pandas as pd
from data_processing import proposal_store
import builtins
import pytest


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


def test_missing_openpyxl_raises(monkeypatch):
    """Ensure a helpful error surfaces when ``openpyxl`` is unavailable."""
    real_import = builtins.__import__

    def fake_import(name, globals=None, locals=None, fromlist=(), level=0):
        if name == "openpyxl":
            raise ImportError("openpyxl is missing")
        return real_import(name, globals, locals, fromlist, level)

    monkeypatch.setattr(builtins, "__import__", fake_import)

    with pytest.warns(UserWarning, match="openpyxl is required"):
        with pytest.raises(ImportError):
            proposal_store.record_proposal("text", None)

