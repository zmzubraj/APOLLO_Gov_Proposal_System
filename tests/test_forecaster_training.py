import json
from pathlib import Path

import numpy as np
import pandas as pd

from src.analysis.train_forecaster import train_model
from src.agents.outcome_forecaster import _apply_model


def test_training_improves_accuracy():
    df = pd.DataFrame(
        {
            "ayes_amount": [50, 50, 50, 50],
            "Total_Voted_DOT": [100, 100, 100, 100],
            "Participants": [50, 50, 50, 50],
            "Eligible_DOT": [100, 100, 100, 100],
            "sentiment_score": [0.8, -0.7, 0.6, -0.5],
            "trend_score": [0.7, -0.6, 0.5, -0.4],
            "Status": ["Executed", "Rejected", "Executed", "Rejected"],
        }
    )

    trained = train_model(df)

    baseline_path = Path(__file__).resolve().parents[1] / "models" / "referendum_model.json"
    with baseline_path.open() as f:
        baseline = json.load(f)

    features = [
        {
            "approval_rate": 0.5,
            "turnout": 0.5,
            "sentiment": s,
            "trending": t,
        }
        for s, t in zip(df["sentiment_score"], df["trend_score"])
    ]
    y = df["Status"].str.lower().eq("executed").astype(float).to_numpy()

    preds_base = np.array([_apply_model(baseline, f) for f in features])
    preds_trained = np.array([_apply_model(trained, f) for f in features])

    brier_base = np.mean((preds_base - y) ** 2)
    brier_trained = np.mean((preds_trained - y) ** 2)
    assert brier_trained < brier_base
    assert np.all((preds_trained >= 0) & (preds_trained <= 1))
