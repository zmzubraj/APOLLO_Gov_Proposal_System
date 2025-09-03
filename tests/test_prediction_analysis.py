import json
from pathlib import Path

import numpy as np
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

    context = {"sentiment_score": 0.2, "trending_score": 0.1}
    result = forecast_outcomes(context)
    assert set(result.keys()) == {"approval_prob", "turnout_estimate"}
    assert 0.0 <= result["approval_prob"] <= 1.0
    assert 0.0 <= result["turnout_estimate"] <= 1.0

    model_path = Path(__file__).resolve().parents[1] / "models" / "referendum_model.json"
    with model_path.open() as f:
        model = json.load(f)
    coeffs = model["coefficients"]
    z = (
        model["intercept"]
        + coeffs.get("approval_rate", 0.0) * 0.5
        + coeffs.get("turnout", 0.0) * 0.5
        + coeffs.get("sentiment", 0.0) * 0.2
        + coeffs.get("trending", 0.0) * 0.1
    )
    expected = 1 / (1 + np.exp(-z))
    assert round(result["approval_prob"], 3) == round(expected, 3)
    assert round(result["turnout_estimate"], 2) == 0.5
