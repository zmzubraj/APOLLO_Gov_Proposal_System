import pandas as pd
from src.data_processing import referenda_updater as ru
from src.data_processing import proposal_store

def test_last_id_and_update_trim_trailing_gaps(tmp_path, monkeypatch):
    path = tmp_path / "gov.xlsx"
    monkeypatch.setattr(ru, "XLSX_PATH", path)
    monkeypatch.setattr(proposal_store, "XLSX_PATH", path)
    base = {c: ("/" if c not in ru.NUMERIC_COLS else 0) for c in ru.COLS}
    valid = base.copy()
    valid.update({
        "Referendum_ID": 1,
        "Start": "2024-01-01 00:00:00",
        "End": "2024-01-02 00:00:00",
        "Status": "Executed",
    })
    gap2 = base.copy(); gap2["Referendum_ID"] = 2
    gap3 = base.copy(); gap3["Referendum_ID"] = 3
    df = pd.DataFrame([valid, gap2, gap3])
    with pd.ExcelWriter(path, engine="openpyxl") as w:
        df.to_excel(w, sheet_name="Referenda", index=False)
    assert ru.last_stored_id() == 1
    def fail(idx):
        row = base.copy(); row["Referendum_ID"] = idx
        raise ru.IncompleteDataError(row, ["Start", "End", "Status"])
    monkeypatch.setattr(ru, "collect_referendum", fail)
    ru.update_referenda(max_new=5, max_gaps=5)
    updated = pd.read_excel(path, sheet_name="Referenda")
    assert updated["Referendum_ID"].tolist() == [1]
