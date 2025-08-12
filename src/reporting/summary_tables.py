"""Utilities for printing summary tables about collected data."""
from __future__ import annotations

from typing import Mapping, Any, Iterable


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

    table = _format_table(headers, rows)
    print(table)


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
    for info in stats:
        pid = info.get("Proposal ID", "-")
        dao = info.get("DAO", "-")
        predicted = info.get("Predicted", "-")
        actual = info.get("Actual", "-")
        confidence = info.get("Confidence")
        confidence_str = f"{confidence:.2f}" if isinstance(confidence, (int, float)) else "-"
        pred_time = info.get("Prediction Time", "-")
        moe = info.get("Margin of Error")
        moe_str = f"{moe:.2f}" if isinstance(moe, (int, float)) else "-"
        rows.append([pid, dao, predicted, actual, confidence_str, pred_time, moe_str])

    if not rows:
        print("No prediction evaluations available")
        return

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

    table = _format_table(headers, rows)
    print(table)
