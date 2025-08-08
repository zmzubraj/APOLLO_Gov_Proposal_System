import pandas as pd
import types, sys


def test_reconcile_referenda_updates_rows(tmp_path, monkeypatch):
    dummy_substrate = types.ModuleType("substrateinterface")
    dummy_substrate.SubstrateInterface = object
    monkeypatch.setitem(sys.modules, "substrateinterface", dummy_substrate)
    from src.data_processing import referenda_updater

    # Prepare fake workbook
    path = tmp_path / "gov.xlsx"
    monkeypatch.setattr(referenda_updater, "XLSX_PATH", path)
    df = pd.DataFrame([
        {
            "Referendum_ID": 1,
            "Title": "old",
            "Content": "/",
            "Start": "",
            "End": "",
            "Duration_days": 0,
            "Participants": 0,
            "ayes_amount": 0,
            "nays_amount": 0,
            "Total_Voted_DOT": 0,
            "Eligible_DOT": 0,
            "Not_Perticipated_DOT": 0,
            "Voted_percentage": 0,
            "Status": "Ongoing",
        }
    ])
    with pd.ExcelWriter(path, engine="openpyxl") as w:
        df.to_excel(w, sheet_name="Referenda", index=False)

    # Mock chain data
    def fake_collect(idx):
        row = df.iloc[0].to_dict()
        row["Title"] = "new"
        return row

    monkeypatch.setattr(referenda_updater, "collect_referendum", lambda idx: fake_collect(idx))

    referenda_updater.reconcile_referenda([1])

    updated = pd.read_excel(path, sheet_name="Referenda")
    assert updated.loc[0, "Title"] == "new"
