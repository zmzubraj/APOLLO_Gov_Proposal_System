import pandas as pd
from data_processing import proposal_store


def test_record_proposal_persists(tmp_path, monkeypatch):
    temp_xlsx = tmp_path / "store.xlsx"
    monkeypatch.setattr(proposal_store, "XLSX_PATH", temp_xlsx)

    proposal_store.record_proposal(
        "Test proposal text", submission_id="ABC123", stage="draft"
    )

    df = pd.read_excel(temp_xlsx, sheet_name="DraftedProposals")

    assert len(df) == 1
    assert df.loc[0, "proposal_text"] == "Test proposal text"
    assert df.loc[0, "submission_id"] == "ABC123"
    assert df.loc[0, "stage"] == "draft"


def test_stage_column_added_if_missing(tmp_path, monkeypatch):
    """Existing sheets lacking ``stage`` gain the column on write."""

    temp_xlsx = tmp_path / "store.xlsx"
    monkeypatch.setattr(proposal_store, "XLSX_PATH", temp_xlsx)

    from openpyxl import Workbook

    wb = Workbook()
    ws = wb.active
    ws.title = "DraftedProposals"
    ws.append(["timestamp", "proposal_text", "submission_id"])
    ws.append(["t1", "Old", "111"])
    wb.save(temp_xlsx)
    wb.close()

    proposal_store.record_proposal("New", submission_id="222", stage="draft")

    df = pd.read_excel(temp_xlsx, sheet_name="DraftedProposals", dtype=str)
    assert "stage" in df.columns
    assert df.loc[df["submission_id"] == "222", "stage"].iat[0] == "draft"


def test_additional_fields_persist(tmp_path, monkeypatch):
    temp_xlsx = tmp_path / "store.xlsx"
    monkeypatch.setattr(proposal_store, "XLSX_PATH", temp_xlsx)

    proposal_store.record_proposal(
        "Extra fields", submission_id="S1", stage="draft", source="chat",
        forecast_confidence=0.8, source_weight=0.5
    )

    df = pd.read_excel(temp_xlsx, sheet_name="DraftedProposals")

    row = df.loc[0]
    assert row["source"] == "chat"
    assert row["forecast_confidence"] == 0.8
    assert row["source_weight"] == 0.5
