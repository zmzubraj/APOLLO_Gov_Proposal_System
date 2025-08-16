import pandas as pd
from data_processing import proposal_store


def test_record_proposal_persists(tmp_path, monkeypatch):
    temp_xlsx = tmp_path / "store.xlsx"
    monkeypatch.setattr(proposal_store, "XLSX_PATH", temp_xlsx)

    proposal_store.record_proposal(
        "Test proposal text", submission_id="ABC123", stage="draft"
    )

    df = pd.read_excel(temp_xlsx, sheet_name="Proposals")

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
    ws.title = "Proposals"
    ws.append(["timestamp", "proposal_text", "submission_id"])
    ws.append(["t1", "Old", "111"])
    wb.save(temp_xlsx)
    wb.close()

    proposal_store.record_proposal("New", submission_id="222", stage="draft")

    df = pd.read_excel(temp_xlsx, sheet_name="Proposals", dtype=str)
    assert "stage" in df.columns
    assert df.loc[df["submission_id"] == "222", "stage"].iat[0] == "draft"
