"""Utilities for storing proposals and execution results in the governance workbook."""
from __future__ import annotations

import pathlib
from typing import Dict, Any, TYPE_CHECKING
import json
import warnings

from utils.helpers import utc_now_iso

ROOT = pathlib.Path(__file__).resolve().parents[2]
DATA_DIR = ROOT / "data"
XLSX_PATH = DATA_DIR / "input" / "PKD Governance Data.xlsx"


if TYPE_CHECKING:
    from openpyxl import Workbook  # type: ignore


def ensure_workbook() -> "Workbook":
    """Create the governance workbook with required sheets if needed.

    Returns the loaded/created workbook.  If ``openpyxl`` is unavailable,
    an informative :class:`ImportError` is raised after emitting a warning.
    When a new workbook is created, the default "Sheet" is removed and the
    workbook is saved containing exactly the sheets
    "Referenda", "Proposals", "Context", and "ExecutionResults".
    """

    try:
        from openpyxl import load_workbook, Workbook  # type: ignore
    except Exception as exc:  # pragma: no cover - exercised in tests via monkeypatch
        warnings.warn(
            "openpyxl is required for storing governance data; install it to enable persistence",
            stacklevel=2,
        )
        raise exc

    XLSX_PATH.parent.mkdir(parents=True, exist_ok=True)
    wb = load_workbook(XLSX_PATH) if XLSX_PATH.exists() else Workbook()

    if "Sheet" in wb.sheetnames:
        wb.remove(wb["Sheet"])

    required = ["Referenda", "Proposals", "Context", "ExecutionResults"]

    for name in required:
        if name not in wb.sheetnames:
            wb.create_sheet(name)

    # Ensure only required sheets remain and are ordered as specified
    for sheet in list(wb.sheetnames):
        if sheet not in required:
            wb.remove(wb[sheet])
    wb._sheets = [wb[name] for name in required]

    wb.save(XLSX_PATH)
    return wb


def _append_row(sheet: str, row: Dict[str, Any]) -> None:
    """Append a dictionary ``row`` to ``sheet`` creating workbook/sheet if needed."""
    wb = ensure_workbook()
    ws = wb[sheet] if sheet in wb.sheetnames else wb.create_sheet(sheet)
    # Write header if sheet empty
    if ws.max_row == 1 and all(cell.value is None for cell in ws[1]):
        ws.delete_rows(1)
        ws.append(list(row.keys()))
    elif ws.max_row == 0:
        ws.append(list(row.keys()))
    ws.append([row.get(col.value, "") for col in ws[1]])
    wb.save(XLSX_PATH)


def record_proposal(
    proposal_text: str,
    submission_id: str | None,
    *,
    stage: str | None = None,
) -> None:
    """Record a generated proposal and optional submission identifier.

    Parameters
    ----------
    proposal_text:
        The text of the proposal.
    submission_id:
        Optional on-chain submission identifier.
    stage:
        Workflow stage of the proposal (e.g. ``"draft"`` or ``"final"``).
        When provided this is persisted alongside the proposal text so that
        intermediate drafts can later be ranked or reviewed.  The argument is
        keyword-only to maintain backwards compatibility with existing calls.
    """

    row = {
        "timestamp": utc_now_iso(),
        "proposal_text": proposal_text,
        "submission_id": submission_id or "",
    }
    if stage is not None:
        row["stage"] = stage
    _append_row("Proposals", row)


def record_execution_result(
    status: str,
    block_hash: str,
    outcome: str,
    submission_id: str | None = None,
    extrinsic_hash: str | None = None,
    referendum_index: int | None = None,
) -> None:
    """Append governor execution details to the ``ExecutionResults`` sheet.

    If ``referendum_index`` is provided, the latest referendum data is
    fetched and stored in the ``Referenda`` sheet via
    :func:`referenda_updater.append_referendum`.
    """
    row = {
        "timestamp": utc_now_iso(),
        "submission_id": submission_id or "",
        "status": status,
        "block_hash": block_hash,
        "outcome": outcome,
        "extrinsic_hash": extrinsic_hash or "",
    }
    _append_row("ExecutionResults", row)

    if referendum_index is not None:
        try:
            from src.data_processing import referenda_updater

            referenda_updater.append_referendum(referendum_index)
        except Exception:
            pass


def record_context(context_dict: Dict[str, Any]) -> None:
    """Record consolidated context blob for auditing."""
    row = {
        "timestamp": utc_now_iso(),
        "context_json": json.dumps(context_dict),
    }
    _append_row("Context", row)


# Reading helpers -----------------------------------------------------------


def load_proposals():
    """Read the ``Proposals`` sheet as a DataFrame (empty if unavailable)."""
    import pandas as pd

    if not XLSX_PATH.exists():
        return pd.DataFrame()
    try:
        return pd.read_excel(XLSX_PATH, sheet_name="Proposals")
    except Exception:
        return pd.DataFrame()


def load_execution_results():
    """Read the ``ExecutionResults`` sheet as a DataFrame (empty if unavailable)."""
    import pandas as pd

    if not XLSX_PATH.exists():
        return pd.DataFrame()
    try:
        return pd.read_excel(XLSX_PATH, sheet_name="ExecutionResults")
    except Exception:
        return pd.DataFrame()


def load_contexts():
    """Read the ``Context`` sheet as a DataFrame (empty if unavailable)."""
    import pandas as pd

    if not XLSX_PATH.exists():
        return pd.DataFrame()
    try:
        return pd.read_excel(XLSX_PATH, sheet_name="Context")
    except Exception:
        return pd.DataFrame()


def retrieve_recent(topics: list[str], limit_per_topic: int = 3) -> list[str]:
    """Return recent proposal/context snippets mentioning any of ``topics``.

    Searches both the ``Proposals`` and ``Context`` sheets for entries
    containing any of the provided topics (case-insensitive) and returns the
    most recent snippets. Results are limited to ``limit_per_topic`` per topic
    and returned in no particular order.
    """

    if not topics:
        return []

    proposals = load_proposals()
    contexts = load_contexts()
    snippets: list[str] = []

    for topic in topics:
        if not isinstance(topic, str) or not topic:
            continue
        if not proposals.empty and "proposal_text" in proposals.columns:
            mask = proposals["proposal_text"].astype(str).str.contains(topic, case=False, na=False)
            snippets.extend(
                proposals.loc[mask]
                .sort_values("timestamp", ascending=False)
                .head(limit_per_topic)["proposal_text"].astype(str).tolist()
            )
        if not contexts.empty and "context_json" in contexts.columns:
            mask = contexts["context_json"].astype(str).str.contains(topic, case=False, na=False)
            snippets.extend(
                contexts.loc[mask]
                .sort_values("timestamp", ascending=False)
                .head(limit_per_topic)["context_json"].astype(str).tolist()
            )

    return snippets


def search_proposals(query: str, limit: int) -> list[str]:
    """Return up to ``limit`` proposal texts containing ``query``.

    Performs a case-insensitive search over the stored proposals using
    pandas' string matching and returns a list of matching snippets.
    """
    import pandas as pd

    if not query:
        return []

    df = load_proposals()
    if df.empty or "proposal_text" not in df.columns:
        return []

    mask = df["proposal_text"].astype(str).str.contains(query, case=False, na=False)
    return df.loc[mask, "proposal_text"].head(limit).tolist()
