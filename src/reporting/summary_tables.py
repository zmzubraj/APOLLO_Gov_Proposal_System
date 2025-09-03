"""Utilities for printing summary tables about collected data."""
from __future__ import annotations

import datetime as dt
import os
import time
import textwrap
from typing import Any, Iterable, Mapping

import pandas as pd

from agents import proposal_generator
from agents.context_generator import build_context
from agents.outcome_forecaster import forecast_outcomes
from analysis.prediction_evaluator import compare_predictions
from data_processing.data_loader import load_governance_data
from data_processing.proposal_store import record_proposal
from utils.helpers import extract_first_heading


try:
    MAX_TITLE_WIDTH = int(os.getenv("MAX_TITLE_WIDTH", "80"))
except ValueError:
    MAX_TITLE_WIDTH = 80


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

    def _is_numeric(text: str) -> bool:
        """Return ``True`` if *text* looks like a number.

        The check is intentionally permissive and strips common characters used
        in the tables (percent signs, tildes, plus/minus etc.) before attempting
        to parse the value as a float.  Empty strings and placeholder dashes are
        treated as non-numeric.
        """

        s = text.strip()
        if not s or s in {"-", "nan", "NaN"}:
            return False
        for ch in (",", "%", "±", "~"):
            s = s.replace(ch, "")
        try:
            float(s)
            return True
        except ValueError:
            return False

    # Determine which columns are numeric
    numeric_cols = [
        rows_str
        and all(_is_numeric(row[i]) or row[i] in {"-", ""} for row in rows_str)
        for i in range(len(headers_str))
    ]

    # Build formatted lines with right alignment for numeric columns
    fmt = " | ".join(
        f"{{:>{w}}}" if numeric_cols[i] else f"{{:<{w}}}" for i, w in enumerate(widths)
    )
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
        ``count``, ``avg_word_length`` and ``update_frequency``. Optional keys
        ``rpc_url``/``platform`` or ``url`` may be supplied for display under the
        ``RPC/URL`` column. ``total_tokens`` may be provided; when absent it is
        estimated as ``count * avg_word_length``. Missing values are represented
        by ``-``.
    """

    headers = [
        "Source Type",
        "RPC/URL",
        "# Documents",
        "Avg. Length (words)",
        "Total token (Data volume)",
        "Update Frequency",
    ]

    source_map = {
        "chat": "Community Chat",
        "forum": "Forum",
        "news": "News Blogs",
        "governance": "Governance Docs",
        "onchain": "On-chain",
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
        if source == "evm_chain":
            continue
        rpc_url = (
            info.get("rpc_url")
            or info.get("platform")
            or info.get("url")
            or "-"
        )
        count = info.get("count", 0)
        avg_len = int(info.get("avg_word_length", 0) or 0)
        total = int(info.get("total_tokens") or count * avg_len)
        freq_raw = str(info.get("update_frequency", "-"))
        freq = freq_map.get(freq_raw.lower(), freq_raw)
        rows.append(
            [
                source_map.get(source, source),
                rpc_url,
                count,
                avg_len,
                total,
                freq,
            ]
        )

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

    if df is None or getattr(df, "empty", True):
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
        was stored in the KB.  A ``source`` key may optionally specify the
        originating data source (e.g. ``chat`` or ``chain``).
    """

    headers = [
        "Source",
        "Batch ID",
        "CTX Size (KB)",
        "Sentiment",
        "Confidence",
        "Embedded in KB",
        "Avg. Src Confidence",
    ]

    # First pass: collect records and aggregate confidence per source
    records: list[dict[str, Any]] = []
    src_conf_sum: dict[str, float] = {}
    src_conf_count: dict[str, int] = {}

    for info in stats:
        source = str(info.get("source", "-"))
        if source == "evm_chain":
            continue
        confidence = float(info.get("confidence", 0.0) or 0.0)
        ctx_size = float(info.get("ctx_size_kb", 0.0) or 0.0)

        records.append(
            {
                "source": source,
                "batch": info.get("batch_id", "-"),
                "ctx_size": ctx_size,
                "sentiment": info.get("sentiment", "-"),
                "confidence": confidence,
                "embedded": "Yes" if info.get("embedded") else "No",
            }
        )

        src_conf_sum[source] = src_conf_sum.get(source, 0.0) + confidence
        src_conf_count[source] = src_conf_count.get(source, 0) + 1

    if not records:
        print("No sentiment batches available")
        return

    avg_conf_per_source = {
        src: (src_conf_sum[src] / src_conf_count[src]) for src in src_conf_sum
    }

    rows = []
    for rec in records:
        avg_src_conf = avg_conf_per_source.get(rec["source"], 0.0)
        source_display = "On-chain" if rec["source"] == "onchain" else rec["source"]
        rows.append(
            [
                source_display,
                rec["batch"],
                f"{rec['ctx_size']:.1f}",
                rec["sentiment"],
                f"{rec['confidence']:.2f}",
                rec["embedded"],
                f"{avg_src_conf:.2f}",
            ]
        )

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
        prediction_time = info.get("prediction_time", 0.0)
        margin = info.get("margin_of_error", 0.0)
        source_key = str(info.get("source", "-"))
        source = source_map.get(source_key.lower(), source_key)
        title = str(info.get("title", "-"))
        if title != "-":
            width = MAX_TITLE_WIDTH
            if width <= len("…"):
                width = len("…") + 1
            title = textwrap.shorten(title, width=width, placeholder="…")
        rows.append(
            [
                source,
                title,
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
    evm_kpis: Mapping[str, Any] | None,
    query: str,
    trending_topics: list[str] | None = None,
) -> dict[str, Any] | None:
    """Draft a proposal using only on-chain metrics."""

    if not chain_kpis:
        return None

    ctx_chain = build_context(
        chain_res,
        {},
        chain_kpis,
        gov_kpis,
        evm_kpis,
        kb_query=query,
        trending_topics=trending_topics,
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
    """Create summary prediction records for each draft.

    The provided ``drafts`` list may be empty if no drafts were generated in the
    current run.  In that case, this function falls back to the persisted
    ``Proposals`` worksheet and produces forecasts for any rows marked with a
    ``stage`` of ``draft``.
    """

    records: list[dict[str, Any]] = []
    seen_texts: set[str] = set()

    for draft in drafts:
        forecast = draft.get("forecast", {})
        approval_prob = forecast.get("approval_prob", 0.0)
        predicted = "Pass" if approval_prob >= threshold else "Fail"
        confidence = approval_prob if predicted == "Pass" else 1 - approval_prob
        text = draft.get("text", "")
        seen_texts.add(text)
        records.append(
            {
                "source": draft.get("source", ""),
                "title": extract_first_heading(text),
                "predicted": predicted,
                "confidence": confidence,
                "prediction_time": draft.get("prediction_time", 0.0),
                "margin_of_error": forecast.get(
                    "margin_of_error", forecast.get("turnout_estimate", 0.0)
                ),
            }
        )

    # Fallback: only load previously stored drafts if none were generated in
    # this run.  Previously this function always appended stored drafts, which
    # led to tables being cluttered with historic entries.  By checking for
    # ``records`` first, we ensure that the summary reflects only the current
    # execution's sources unless no new drafts were produced.
    if not records:
        try:
            from data_processing.proposal_store import load_proposals

            df = load_proposals()
            if not df.empty:
                stage_col = (
                    df.columns[df.columns.str.lower() == "stage"].tolist() or [None]
                )[0]
                text_col = (
                    df.columns[df.columns.str.lower() == "proposal_text"].tolist()
                    or [None]
                )[0]
                if text_col:
                    if stage_col:
                        mask = (
                            df[stage_col].astype(str).str.lower() == "draft"
                        )
                        df = df[mask]
                    for text in df[text_col].astype(str):
                        if text in seen_texts:
                            continue
                        t_pred = time.perf_counter()
                        forecast = forecast_outcomes({})
                        prediction_time = time.perf_counter() - t_pred
                        approval_prob = forecast.get("approval_prob", 0.0)
                        predicted = (
                            "Pass" if approval_prob >= threshold else "Fail"
                        )
                        confidence = (
                            approval_prob if predicted == "Pass" else 1 - approval_prob
                        )
                        records.append(
                            {
                                "source": "stored",
                                "title": extract_first_heading(text),
                                "predicted": predicted,
                                "confidence": confidence,
                                "prediction_time": prediction_time,
                                "margin_of_error": forecast.get(
                                    "margin_of_error",
                                    forecast.get("turnout_estimate", 0.0),
                                ),
                            }
                        )
        except Exception:
            pass

    return records
