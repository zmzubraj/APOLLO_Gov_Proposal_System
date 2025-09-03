"""Train and update the referendum outcome forecasting model."""
from __future__ import annotations

import json
from pathlib import Path
import sys

import pandas as pd

ROOT = Path(__file__).resolve().parents[1]
sys.path.append(str(ROOT))

from src.data_processing.data_loader import load_governance_data  # noqa: E402
from src.agents.outcome_forecaster import MODEL_PATH  # noqa: E402

try:  # pragma: no cover - training is optional in tests
    from sklearn.linear_model import LogisticRegression
except Exception:  # pragma: no cover
    LogisticRegression = None


def _prepare_features(df: pd.DataFrame) -> tuple[pd.DataFrame, pd.Series]:
    """Return feature matrix ``X`` and target ``y`` from ``df``."""
    status = df.get("Status", pd.Series(dtype=str)).astype(str).str.lower()
    y = status.eq("executed").astype(int)

    if "Voted_percentage" in df.columns:
        turnout = df["Voted_percentage"].astype(float) / 100.0
    elif {"Participants", "Eligible_DOT"}.issubset(df.columns):
        turnout = (
            df["Participants"].astype(float)
            / df["Eligible_DOT"].replace(0, pd.NA).astype(float)
        ).fillna(0)
    else:
        turnout = pd.Series(0.0, index=df.index)

    proposal_len = (
        df.get("proposal_text", pd.Series("", index=df.index))
        .astype(str)
        .apply(lambda s: float(len(s.split())))
    )

    approval_rate = y.expanding().mean().shift(1).fillna(y.mean())
    turnout_trend = turnout.diff().rolling(window=3).mean().shift(1).fillna(0.0)

    X = pd.DataFrame(
        {
            "approval_rate": approval_rate,
            "turnout": turnout,
            "sentiment": 0.0,
            "trending": 0.0,
            "proposal_length": proposal_len,
            "engagement_weight": 0.0,
            "turnout_trend": turnout_trend,
        }
    )
    return X, y


def main() -> None:
    df = load_governance_data(sheet_name="Referenda")
    if df.empty:
        print("No referendum data available; model not updated")
        return

    X, y = _prepare_features(df)

    if LogisticRegression is None:
        print("scikit-learn not installed; cannot train model")
        return

    model = LogisticRegression(max_iter=1000)
    model.fit(X, y)

    out = {
        "intercept": float(model.intercept_[0]),
        "coefficients": {name: float(coef) for name, coef in zip(X.columns, model.coef_[0])},
    }
    MODEL_PATH.write_text(json.dumps(out, indent=2))
    print(f"Model updated at {MODEL_PATH}")


if __name__ == "__main__":
    main()
