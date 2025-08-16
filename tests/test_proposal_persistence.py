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
