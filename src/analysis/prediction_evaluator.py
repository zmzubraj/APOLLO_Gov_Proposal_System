"""Utilities for comparing forecasted referendum outcomes with reality."""
from __future__ import annotations

from typing import Dict, List, Any

import pandas as pd

try:  # Prefer absolute import so tests can patch via ``src.data_processing``
    from src.data_processing.data_loader import load_governance_data
except Exception:  # pragma: no cover - fallback for runtime package layout
    from data_processing.data_loader import load_governance_data


def _normalise_columns(df: pd.DataFrame) -> pd.DataFrame:
    """Return a copy of ``df`` with lower snake_case column names."""
    df = df.copy()
    df.columns = [c.strip().lower().replace(" ", "_") for c in df.columns]
    return df


def compare_predictions(
    df_predictions: pd.DataFrame,
    df_actual: pd.DataFrame | None = None,
) -> Dict[str, List[Dict[str, Any]]]:
    """Join forecasts with historical outcomes and store under ``prediction_eval``.

    Parameters
    ----------
    df_predictions:
        DataFrame containing forecasted outcomes with columns such as
        ``proposal_id``, ``dao``, ``predicted``, ``confidence``,
        ``prediction_time`` and ``margin_of_error``.
    df_actual:
        Historical referendum data. If ``None`` the ``Referenda`` sheet is
        loaded via :func:`data_processing.data_loader.load_governance_data`.

    Returns
    -------
    dict
        ``{"prediction_eval": [...]}`` where each row holds
        ``Proposal ID``, ``DAO``, ``Predicted``, ``Actual``, ``Confidence``,
        ``Prediction Time`` and ``Margin of Error``.
    """
    if df_actual is None or df_actual.empty:
        df_actual = load_governance_data(sheet_name="Referenda")
        if isinstance(df_actual, dict):
            df_actual = next(iter(df_actual.values()))

    if df_predictions is None or df_predictions.empty or df_actual is None or df_actual.empty:
        return {"prediction_eval": []}

    pred = _normalise_columns(df_predictions)
    actual = _normalise_columns(df_actual)

    # Prefer matching by both proposal_id and dao; if that fails, fall back to
    # a canonicalised DAO key, and finally to proposal_id only. This helps when
    # historical sheets use slightly different DAO labels (e.g. "DOT Gov").
    def _canon(v: Any) -> str:
        s = str(v or "").strip().lower().replace(" ", "")
        return s or "gov"

    merged = pred.merge(
        actual[["proposal_id", "dao", "actual"]],
        on=["proposal_id", "dao"],
        how="left",
    )
    if merged["actual"].isna().all():
        pred_key = pred.copy()
        act_key = actual.copy()
        pred_key["dao_key"] = pred_key.get("dao", "").map(_canon) if "dao" in pred_key else "gov"
        act_key["dao_key"] = act_key.get("dao", "").map(_canon) if "dao" in act_key else "gov"
        merged = pred_key.merge(
            act_key[["proposal_id", "dao_key", "actual"]],
            on=["proposal_id", "dao_key"],
            how="left",
        )
        # restore expected columns for downstream rename
        if "dao" not in merged and "dao_key" in merged:
            merged["dao"] = merged["dao_key"]
    if merged["actual"].isna().all():
        merged = pred.merge(
            actual[["proposal_id", "actual"]],
            on=["proposal_id"],
            how="left",
        )
        if "dao" not in merged:
            merged["dao"] = pred.get("dao", "Gov")

    # Ensure required columns exist
    for col in [
        "proposal_id",
        "dao",
        "predicted",
        "actual",
        "confidence",
        "prediction_time",
        "margin_of_error",
    ]:
        if col not in merged:
            merged[col] = pd.NA

    column_map = {
        "proposal_id": "Proposal ID",
        "dao": "DAO",
        "predicted": "Predicted",
        "actual": "Actual",
        "confidence": "Confidence",
        "prediction_time": "Prediction Time",
        "margin_of_error": "Margin of Error",
    }
    result = merged.rename(columns=column_map)

    rows = result[
        [
            "Proposal ID",
            "DAO",
            "Predicted",
            "Actual",
            "Confidence",
            "Prediction Time",
            "Margin of Error",
        ]
    ].to_dict("records")

    return {"prediction_eval": rows}
