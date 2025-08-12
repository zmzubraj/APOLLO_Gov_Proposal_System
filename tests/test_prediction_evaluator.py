import pandas as pd
from src.analysis.prediction_evaluator import compare_predictions


def test_compare_predictions_merges_and_returns_stats():
    df_pred = pd.DataFrame(
        {
            "proposal_id": [1],
            "dao": ["DAO1"],
            "predicted": ["Approved"],
            "confidence": [0.9],
            "prediction_time": ["2024-01-01"],
            "margin_of_error": [0.05],
        }
    )

    df_act = pd.DataFrame(
        {
            "proposal_id": [1],
            "dao": ["DAO1"],
            "actual": ["Rejected"],
        }
    )

    stats = compare_predictions(df_pred, df_act)
    assert "prediction_eval" in stats
    row = stats["prediction_eval"][0]
    assert row["Proposal ID"] == 1
    assert row["DAO"] == "DAO1"
    assert row["Predicted"] == "Approved"
    assert row["Actual"] == "Rejected"
    assert row["Confidence"] == 0.9
    assert row["Prediction Time"] == "2024-01-01"
    assert row["Margin of Error"] == 0.05
