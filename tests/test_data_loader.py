import pandas as pd
from pathlib import Path

from data_processing import data_loader


def _fake_read_excel(*args, **kwargs):
    raise FileNotFoundError


def test_missing_workbook_returns_all_empty(monkeypatch, tmp_path):
    fake_path = tmp_path / "missing.xlsx"
    monkeypatch.setattr(data_loader, "FILE_PATH", fake_path)
    monkeypatch.setattr(data_loader, "XLSX_PATH", fake_path)
    monkeypatch.setattr(data_loader, "ensure_workbook", lambda: None)
    monkeypatch.setattr(data_loader.pd, "read_excel", _fake_read_excel)

    data = data_loader.load_governance_data()

    assert set(data.keys()) == {
        "Referenda",
        "DraftedProposals",
        "Proposal",
        "ExecutionResults",
        "Context",
    }
    assert all(isinstance(df, pd.DataFrame) and df.empty for df in data.values())


def test_missing_workbook_context_sheet(monkeypatch, tmp_path):
    fake_path = tmp_path / "missing.xlsx"
    monkeypatch.setattr(data_loader, "FILE_PATH", fake_path)
    monkeypatch.setattr(data_loader, "XLSX_PATH", fake_path)
    monkeypatch.setattr(data_loader, "ensure_workbook", lambda: None)
    monkeypatch.setattr(data_loader.pd, "read_excel", _fake_read_excel)

    df = data_loader.load_governance_data(sheet_name="Context")

    assert isinstance(df, pd.DataFrame)
    assert df.empty
