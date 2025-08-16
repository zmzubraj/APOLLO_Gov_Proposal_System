import pandas as pd
from src.reporting.summary_tables import evaluate_historical_predictions


def test_historical_prediction_fallback(monkeypatch):
    # DataFrame with three completed referenda and one ongoing
    df = pd.DataFrame(
        {
            "Referendum_ID": [1, 2, 3, 4],
            "Status": ["Approved", "Rejected", "Passed", "Ongoing"],
            "Title": ["T1", "T2", "T3", "T4"],
        }
    )

    # Patch data loading used by evaluation and forecasting
    monkeypatch.setattr(
        "src.reporting.summary_tables.load_governance_data", lambda sheet_name="Referenda": df
    )
    monkeypatch.setattr(
        "src.agents.outcome_forecaster.load_governance_data", lambda sheet_name="Referenda": df
    )

    # Ensure deterministic sampling
    monkeypatch.setenv("HISTORICAL_SAMPLE_SEED", "0")

    results = evaluate_historical_predictions(sample_size=5)

    # Only three referenda are eligible despite requesting five
    assert len(results) == 3

    # Sample order should be deterministic due to seed
    assert [r["Proposal ID"] for r in results] == [3, 2, 1]

    for res in results:
        assert res.get("Predicted")
        assert res.get("Actual")
