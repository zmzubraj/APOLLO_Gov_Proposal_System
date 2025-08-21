"""Utilities for printing summary tables about collected data."""
from __future__ import annotations

import datetime as dt
import os
import time
from typing import Any, Iterable, Mapping

import pandas as pd

from agents import proposal_generator
from agents.context_generator import build_context
from agents.outcome_forecaster import forecast_outcomes
from analysis.prediction_evaluator import compare_predictions
from data_processing.data_loader import load_governance_data
from data_processing.proposal_store import load_proposals, record_proposal
from utils.helpers import extract_first_heading


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
        "Avg. Length (words)",
        "Update Frequency",
        ]

    source_map = {
        "chat": "Community Chat",
        "forum": "Forum",
        "news": "News Blogs",
        "governance": "Governance Docs",
        "chain": "Voting Histories",
    }
    freq_map = {
        "daily": "Daily",
        "hourly": "Hourly",
        "realtime": "Real time",
        "real time": "Real time",
        "every run": "Every Run",
        "every_run": "Every Run",
        "~6s": "~6 sec",
        "~6 sec": "~6 sec",
        "≈6s": "~6 sec",
    }

    rows = []
    for source, info in stats.items():
        platform = info.get("platform") or info.get("url") or "-"
        count = info.get("count", 0)
        avg_len = int(info.get("avg_word_length", 0) or 0)
        freq_raw = str(info.get("update_frequency", "-"))
        freq = freq_map.get(freq_raw.lower(), freq_raw)
        rows.append([source_map.get(source, source), platform, count, avg_len, freq])

    if not rows:
        print("No data sources available")
        return

    print("\nTable: Data Sources and Scraping Volume")
    table = _format_table(headers, rows)
    print(table)


def print_timing_benchmarks_table(stats: Iterable[Mapping[str, Any]]) -> None:
    """Print a table summarising pipeline timing benchmarks.

    Parameters
    ----------
    stats:
        Iterable of timing dictionaries, typically the last few runs. Each
        dictionary should contain the keys ``scenario``, ``proposals``,
        ``ingestion_s``, ``analysis_prediction_s`` and ``draft_sign_s``
        representing the duration of each phase in seconds.
    """

    headers = [
        "Scenario",
        "# Proposals",
        "Ingestion (s)",
        "Analysis + Prediction (s)",
        "Draft + Sign (s)",
        "Total Time (s)",
    ]

    scenario_labels = {
        "light": "Light Load",
        "light load": "Light Load",
        "medium": "Medium Load",
        "medium load": "Medium Load",
        "high": "High Load",
        "high load": "High Load",
    }

    rows = []
    for info in stats:
        scenario_raw = str(info.get("scenario", "-"))
        scenario_display = scenario_labels.get(scenario_raw.lower(), scenario_raw)
        proposals = info.get("proposals", 0)
        ingestion = info.get("ingestion_s", 0.0)
        analysis = info.get("analysis_prediction_s", 0.0)
        draft = info.get("draft_sign_s", 0.0)
        total = ingestion + analysis + draft
        rows.append(
            [
                scenario_display,
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
            seed_val = int(seed)
            if seed_val != 0:
                sample_kwargs["random_state"] = seed_val
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

        t_pred = time.perf_counter()
        forecast = forecast_outcomes(context)
        prediction_time = time.perf_counter() - t_pred
        prob = forecast.get("approval_prob", 0.0)
        predicted = "Approved" if prob >= 0.5 else "Rejected"

        dao_col = col_map.get("dao")
        predictions.append(
            {
                "proposal_id": row.get(id_col),
                "dao": row.get(dao_col, "Gov") if dao_col else "Gov",
                "predicted": predicted,
                "confidence": prob,
                "prediction_time": prediction_time,
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
        ``DAO``, ``Predicted``, ``Actual``, ``Confidence``,
        ``Prediction Time`` and ``Margin of Error``.
    """

    headers = [
        "Proposal ID",
        "DAO",
        "Predicted",
        "Actual",
        "Confidence (%)",
        "Prediction Time (s)",
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
        if isinstance(confidence, (int, float)):
            confidence_str = f"{confidence * 100:.2f}%"
        else:
            confidence_str = "-"

        pred_time_val = info.get("Prediction Time")
        if isinstance(pred_time_val, (int, float)):
            pred_time = f"{pred_time_val:.2f}"
        else:
            pred_time = str(pred_time_val or "-")

        moe = info.get("Margin of Error")
        if isinstance(moe, (int, float)):
            moe_str = f"±{moe * 100:.2f}%"
        else:
            moe_str = "-"

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
        with the keys ``batch_id``, ``ctx_size_kb`` (CTX size in KB),
        ``sentiment``, ``confidence`` and ``embedded`` specifying if the batch
        was stored in the KB.
    """

    headers = [
        "Batch ID",
        "CTX Size (KB)",
        "Sentiment",
        "Confidence",
        "Embedded in KB",
    ]

    rows = []
    for info in stats:
        batch = info.get("batch_id", "-")
        size = f"{info.get('ctx_size_kb', 0.0):.1f}"
        sent = info.get("sentiment", "-")
        conf = f"{info.get('confidence', 0.0):.2f}"
        embedded = "Yes" if info.get("embedded") else "No"
        rows.append([batch, size, sent, conf, embedded])

    if not rows:
        print("No sentiment batches available")
        return

    print("\nTable: Sentiment Analysis and Knowledge Base Embedding")
    table = _format_table(headers, rows)
    print(table)


def print_draft_forecast_table(
    stats: Iterable[Mapping[str, Any]], threshold: float
) -> None:
    """Print a table of proposal draft outcome forecasts."""

    headers = [
        "Source Type",
        "Title",
        "Predicted",
        "Confidence (%)",
        "Prediction Time (s)",
        "Margin of Error",
    ]

    source_map = {
        "forum": "Forum",
        "chat": "Chat",
        "news": "News",
        "onchain": "Onchain",
    }

    rows = []
    for info in stats:
        confidence = info.get("confidence", 0.0)
        predicted = str(info.get("predicted", ""))
        if predicted.lower() == "pass" and confidence >= threshold:
            continue
        prediction_time = info.get("prediction_time", 0.0)
        margin = info.get("margin_of_error", 0.0)
        source_key = str(info.get("source", "-"))
        source = source_map.get(source_key.lower(), source_key)
        rows.append(
            [
                source,
                info.get("title", "-"),
                info.get("predicted", "-"),
                f"{confidence * 100:.0f}%",
                f"{prediction_time:.1f}",
                f"±{margin * 100:.0f}%",
            ]
        )

    if not rows:
        print("No draft predictions available")
        return

    print(
        "\nTable: Drafted proposal success prediction and forecast "
        f"(Pass confidence threshold <{threshold * 100:.0f}%)"
    )
    table = _format_table(headers, rows)
    print(table)


def draft_onchain_proposal(
    chain_res: Mapping[str, Any],
    chain_kpis: Mapping[str, Any],
    gov_kpis: Mapping[str, Any],
    query: str,
) -> dict[str, Any] | None:
    """Draft a proposal using only on-chain metrics."""

    if not chain_kpis:
        return None

    ctx_chain = build_context(
        chain_res,
        {},
        chain_kpis,
        gov_kpis,
        kb_query=query,
        summarise_snippets=True,
    )
    chain_draft = proposal_generator.draft(ctx_chain)
    t_pred = time.perf_counter()
    chain_forecast = forecast_outcomes(ctx_chain)
    prediction_time = time.perf_counter() - t_pred
    ctx_chain["forecast"] = chain_forecast
    record_proposal(chain_draft, None, stage="draft")
    return {
        "source": "onchain",
        "text": chain_draft,
        "context": ctx_chain,
        "forecast": chain_forecast,
        "prediction_time": prediction_time,
    }


def summarise_draft_predictions(
    drafts: list[dict[str, Any]], threshold: float
) -> list[dict[str, Any]]:
    """Create summary prediction records for each draft."""
    records: list[dict[str, Any]] = []
    for draft in drafts:
        forecast = draft.get("forecast", {})
        approval_prob = forecast.get("approval_prob", 0.0)
        predicted = "Pass" if approval_prob >= threshold else "Fail"
        confidence = approval_prob if predicted == "Pass" else 1 - approval_prob
        records.append(
            {
                "source": draft.get("source", ""),
                "title": extract_first_heading(draft.get("text", "")),
                "predicted": predicted,
                "confidence": confidence,
                "prediction_time": draft.get("prediction_time", 0.0),
                "margin_of_error": forecast.get(
                    "margin_of_error", forecast.get("turnout_estimate", 0.0)
                ),
            }
        )
    return records


def load_persisted_draft_predictions(threshold: float) -> list[dict[str, Any]]:
    """Return prediction summaries for proposals stored in the workbook.

    This reads the ``Proposals`` sheet and forecasts outcomes for any rows
    marked with ``stage`` == ``"draft"``.  Each stored draft is processed in
    isolation using the naive :func:`forecast_outcomes` agent and then
    summarised via :func:`summarise_draft_predictions`.
    """

    df = load_proposals()
    if df.empty or "proposal_text" not in df.columns:
        return []

    if "stage" in df.columns:
        mask = df["stage"].astype(str).str.lower() == "draft"
        texts = df.loc[mask, "proposal_text"].dropna().tolist()
    else:
        texts = df["proposal_text"].dropna().tolist()

    drafts: list[dict[str, Any]] = []
    for text in texts:
        t_pred = time.perf_counter()
        forecast = forecast_outcomes({})
        prediction_time = time.perf_counter() - t_pred
        drafts.append(
            {
                "source": "archive",
                "text": text,
                "forecast": forecast,
                "prediction_time": prediction_time,
            }
        )

    return summarise_draft_predictions(drafts, threshold)
