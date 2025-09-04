import types, sys

def test_record_execution_updates_referenda(tmp_path, monkeypatch):
    from src.data_processing import proposal_store

    dummy = types.ModuleType("referenda_updater")
    called = {}

    def fake_append(idx):
        called["idx"] = idx

    dummy.append_referendum = fake_append
    monkeypatch.setitem(sys.modules, "src.data_processing.referenda_updater", dummy)
    import src.data_processing as dp
    monkeypatch.setattr(dp, "referenda_updater", dummy, raising=False)
    monkeypatch.setattr(proposal_store, "XLSX_PATH", tmp_path / "gov.xlsx")

    proposal_store.record_execution_result(
        status="Executed",
        block_hash="0x",
        outcome="Approved",
        submission_id="1",
        extrinsic_hash="0x",
        referendum_index=42,
    )

    assert called.get("idx") == 42


def test_execution_result_links_to_proposal(tmp_path, monkeypatch):
    from src.data_processing import proposal_store

    temp_xlsx = tmp_path / "store.xlsx"
    monkeypatch.setattr(proposal_store, "XLSX_PATH", temp_xlsx)

    proposal_store.record_proposal("Draft", None, stage="draft")
    proposal_store.record_proposal("Final", "SID", stage="submitted")

    proposal_store.record_execution_result(
        status="Executed",
        block_hash="0x",
        outcome="Approved",
        submission_id="SID",
    )

    import pandas as pd

    df_exec = pd.read_excel(temp_xlsx, sheet_name="ExecutionResults")
    df_prop = pd.read_excel(temp_xlsx, sheet_name="Proposal")
    submitted_row = df_prop.index[df_prop["submission_id"] == "SID"][0] + 2
    assert int(df_exec.loc[0, "proposal_row"]) == submitted_row
