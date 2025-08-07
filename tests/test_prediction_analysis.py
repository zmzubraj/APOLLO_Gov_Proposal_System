import pandas as pd
from src.agents.outcome_forecaster import forecast_outcomes
from src.data_processing import data_loader


def test_forecast_outcomes_fields_and_ranges(tmp_path, monkeypatch):
    df = pd.DataFrame(
        {
            "Status": ["Executed", "Rejected"],
            "Voted_percentage": [60.0, 40.0],
            "Participants": [100, 80],
            "Eligible_DOT": [200, 200],
        }
    )
    path = tmp_path / "PKD Governance Data.xlsx"
    df.to_excel(path, sheet_name="Referenda", index=False)
    monkeypatch.setattr(data_loader, "FILE_PATH", path)

    result = forecast_outcomes({})
    assert set(result.keys()) == {"approval_prob", "turnout_estimate"}
    assert 0.0 <= result["approval_prob"] <= 1.0
    assert 0.0 <= result["turnout_estimate"] <= 1.0
    assert round(result["approval_prob"], 2) == 0.5
    assert round(result["turnout_estimate"], 2) == 0.5
