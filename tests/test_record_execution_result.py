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
