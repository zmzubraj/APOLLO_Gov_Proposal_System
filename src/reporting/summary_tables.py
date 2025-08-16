"""Utilities for printing summary tables about collected data."""
from __future__ import annotations

import datetime as dt
import os
from typing import Any, Iterable, Mapping

import pandas as pd

from agents.outcome_forecaster import forecast_outcomes
from analysis.prediction_evaluator import compare_predictions
from data_processing.data_loader import load_governance_data


def _format_table(headers: Iterable[str], rows: Iterable[Iterable[Any]]) -> str:
    """Return a simple ASCII table string.

    This helper determines column widths based on the longest entry in each
    column and creates a plain table using ``|`` and ``-`` characters.  It is
    intentionally lightweight to avoid extra dependencies.
    """

    # Convert all cells to strings for width calculation
    rows_str = [[str(c) for c in row] for row in rows]
    headers_str = [str(h) for h in headers]

    # Determine column widths
    widths = [
        max(len(headers_str[i]), *(len(row[i]) for row in rows_str))
        if rows_str
        else len(headers_str[i])
        for i in range(len(headers_str))
    ]

    # Build formatted lines
    fmt = " | ".join(f"{{:<{w}}}" for w in widths)
    sep = "-+-".join("-" * w for w in widths)

    lines = [fmt.format(*headers_str), sep]
    for row in rows_str:
        lines.append(fmt.format(*row))
    return "\n".join(lines)


def print_data_sources_table(stats: Mapping[str, Mapping[str, Any]]) -> None:
    """Print a table summarising the collected data sources.

    Parameters
    ----------
    stats:
        Mapping of source type to a dictionary containing at least the keys
        ``count``, ``avg_word_length`` and ``update_frequency``.  Optional keys
        ``platform`` or ``url`` may be supplied for display under the
        ``Platform/URL`` column.  Missing values are represented by ``-``.
    """

    headers = [
        "Source Type",
        "Platform/URL",
        "# Documents",
        "Avg. Length",
        "Update Frequency",
        ]

    rows = []
    for source, info in stats.items():
        platform = info.get("platform") or info.get("url") or "-"
        count = info.get("count", 0)
        avg_len = f"{info.get('avg_word_length', 0):.1f}"
        freq = info.get("update_frequency", "-")
        rows.append([source, platform, count, avg_len, freq])

    if not rows:
        print("No data sources available")
        return

    print("\nTable: Data Sources and Scraping Volume")
    table = _format_table(headers, rows)
    print(table)


def print_timing_benchmarks_table(stats: Mapping[str, Any]) -> None:
    """Print a table summarising pipeline timing benchmarks.

    Parameters
    ----------
    stats:
        Mapping of scenario names to dictionaries describing timing
        information. Each dictionary should contain at least the keys
        ``proposals``, ``ingestion_s``, ``analysis_prediction_s`` and
        ``draft_sign_s`` representing the duration of each phase in
        seconds.
    """

    headers = [
        "Scenario",
        "# Proposals",
        "Ingestion (s)",
        "Analysis + Prediction (s)",
        "Draft + Sign (s)",
        "Total (s)",
    ]

    rows = []
    for scenario, info in stats.items():
        if not isinstance(info, Mapping):
            # If a list of runs is provided, aggregate by averaging
            runs = list(info)
            if not runs:
                continue
            proposals = sum(r.get("proposals", 0) for r in runs) / len(runs)
            ingestion = sum(r.get("ingestion_s", 0.0) for r in runs) / len(runs)
            analysis = sum(
                r.get("analysis_prediction_s", 0.0) for r in runs
            ) / len(runs)
            draft = sum(r.get("draft_sign_s", 0.0) for r in runs) / len(runs)
        else:
            proposals = info.get("proposals", 0)
            ingestion = info.get("ingestion_s", 0.0)
            analysis = info.get("analysis_prediction_s", 0.0)
            draft = info.get("draft_sign_s", 0.0)

        total = ingestion + analysis + draft
        rows.append(
            [
                scenario,
                f"{proposals:.0f}",
                f"{ingestion:.2f}",
                f"{analysis:.2f}",
                f"{draft:.2f}",
                f"{total:.2f}",
            ]
        )

    if not rows:
        print("No timing benchmarks available")
        return

    print("\nTable: End-to-End Timing Benchmarks")
    table = _format_table(headers, rows)
    print(table)


def evaluate_historical_predictions(sample_size: int = 5) -> list[dict[str, Any]]:
    """Compare naive forecasts against historical referendum outcomes.

    Parameters
    ----------
    sample_size:
        Maximum number of historical rows to evaluate. Defaults to ``5``.

    Returns
    -------
    list
        List of prediction evaluation dictionaries. Empty if prerequisites
        are missing.
    """

    try:
        df = load_governance_data(sheet_name="Referenda")
        if isinstance(df, dict):
            df = next(iter(df.values()))
    except Exception:
        return []

    if df is None or df.empty:
        return []

    col_map = {c.lower().replace(" ", "_"): c for c in df.columns}

    status_col = next(
        (col_map[c] for c in ["status", "state", "result", "outcome"] if c in col_map),
        None,
    )
    id_col = next(
        (
            col_map[c]
            for c in ["proposal_id", "referendum_id", "id", "referendum"]
            if c in col_map
        ),
        None,
    )
    if status_col is None or id_col is None:
        return []

    finished_mask = (
        df[status_col]
        .astype(str)
        .str.lower()
        .isin(
            [
                "executed",
                "approved",
                "rejected",
                "failed",
                "passed",
                "completed",
                "finished",
            ]
        )
    )
    df_done = df[finished_mask]
    if df_done.empty:
        return []

    seed = os.getenv("HISTORICAL_SAMPLE_SEED")
    sample_kwargs = {"n": min(sample_size, len(df_done))}
    if seed:
        try:
            sample_kwargs["random_state"] = int(seed)
        except ValueError:
            pass

    sample_df = df_done.sample(**sample_kwargs)

    title_col = next((col_map[c] for c in ["title", "name"] if c in col_map), None)
    summary_col = next(
        (col_map[c] for c in ["summary", "content", "description"] if c in col_map),
        None,
    )

    predictions: list[dict[str, Any]] = []
    for _, row in sample_df.iterrows():
        context = {}
        if title_col:
            context["title"] = row.get(title_col, "")
        if summary_col:
            context["summary"] = row.get(summary_col, "")

        forecast = forecast_outcomes(context)
        prob = forecast.get("approval_prob", 0.0)
        predicted = "Approved" if prob >= 0.5 else "Rejected"

        dao_col = col_map.get("dao")
        predictions.append(
            {
                "proposal_id": row.get(id_col),
                "dao": row.get(dao_col, "Gov") if dao_col else "Gov",
                "predicted": predicted,
                "confidence": prob,
                "prediction_time": dt.datetime.now(dt.UTC).isoformat(),
                "margin_of_error": forecast.get("turnout_estimate", 0.0),
            }
        )

    df_pred = pd.DataFrame(predictions)
    if df_pred.empty:
        return []

    df_actual = df_done.rename(columns={id_col: "proposal_id", status_col: "actual"})
    dao_col = col_map.get("dao")
    if dao_col:
        df_actual = df_actual.rename(columns={dao_col: "dao"})
    else:
        df_actual["dao"] = "Gov"
    df_actual = df_actual[["proposal_id", "dao", "actual"]]

    eval_res = compare_predictions(df_pred, df_actual)
    return eval_res.get("prediction_eval", [])


def print_prediction_accuracy_table(stats: Iterable[Mapping[str, Any]]) -> None:
    """Print a table comparing forecasted outcomes with actual results.

    Parameters
    ----------
    stats:
        Iterable of dictionaries each containing the keys ``Proposal ID``,
        ``DAO``, ``Predicted``, ``Actual``, ``Confidence``, ``Prediction Time``
        and ``Margin of Error``.
    """

    headers = [
        "Proposal ID",
        "DAO",
        "Predicted",
        "Actual",
        "Confidence",
        "Prediction Time",
        "Margin of Error",
    ]

    rows = []
    has_actual = False
    for info in stats:
        pid = info.get("Proposal ID", "-")
        dao = info.get("DAO", "-")
        predicted = info.get("Predicted", "-")
        actual = info.get("Actual", "-")
        if actual not in (None, "", "-", "nan", "NaN"):
            has_actual = True
        confidence = info.get("Confidence")
        confidence_str = f"{confidence:.2f}" if isinstance(confidence, (int, float)) else "-"
        pred_time = info.get("Prediction Time", "-")
        moe = info.get("Margin of Error")
        moe_str = f"{moe:.2f}" if isinstance(moe, (int, float)) else "-"
        rows.append([pid, dao, predicted, actual, confidence_str, pred_time, moe_str])

    if not rows:
        print("No prediction evaluations available")
        return

    title = "Table: Voting Result Prediction vs. Actual Outcomes"
    if has_actual:
        title += " (historical referenda data)"
    else:
        title += " (current data)"
    print(f"\n{title}")
    table = _format_table(headers, rows)
    print(table)


def print_sentiment_embedding_table(stats: Iterable[Mapping[str, Any]]) -> None:
    """Print a table summarising sentiment analysis batches.

    Parameters
    ----------
    stats:
        Iterable of dictionaries each describing one sentiment analysis batch
        with the keys ``batch_id``, ``source``, ``ctx_size_kb``, ``sentiment``,
        ``confidence`` and ``embedded``.
    """

    headers = [
        "Batch",
        "Source",
        "Ctx Size (KB)",
        "Sentiment",
        "Confidence",
        "Embedded",
    ]

    rows = []
    for info in stats:
        batch = info.get("batch_id", "-")
        source = info.get("source", "-")
        size = f"{info.get('ctx_size_kb', 0.0):.1f}"
        sent = info.get("sentiment", "-")
        conf = f"{info.get('confidence', 0.0):.2f}"
        embedded = "yes" if info.get("embedded") else "no"
        rows.append([batch, source, size, sent, conf, embedded])

    if not rows:
        print("No sentiment batches available")
        return

    print("\nTable: Sentiment Analysis and Knowledge Base Embedding")
    table = _format_table(headers, rows)
    print(table)
