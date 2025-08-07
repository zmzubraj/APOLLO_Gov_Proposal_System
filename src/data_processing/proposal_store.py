"""Utilities for storing proposals and execution results in the governance workbook."""
from __future__ import annotations

import pathlib
from typing import Dict, Any
import json

from src.utils.helpers import utc_now_iso

ROOT = pathlib.Path(__file__).resolve().parents[2]
DATA_DIR = ROOT / "data"
XLSX_PATH = DATA_DIR / "input" / "PKD Governance Data.xlsx"


def _append_row(sheet: str, row: Dict[str, Any]) -> None:
    """Append a dictionary ``row`` to ``sheet`` creating workbook/sheet if needed."""
    try:
        from openpyxl import load_workbook, Workbook  # type: ignore
    except Exception:
        # Openpyxl (or its deps) not available – skip persistence silently
        return

    XLSX_PATH.parent.mkdir(parents=True, exist_ok=True)
    if XLSX_PATH.exists():
        wb = load_workbook(XLSX_PATH)
    else:
        wb = Workbook()
    ws = wb[sheet] if sheet in wb.sheetnames else wb.create_sheet(sheet)
    # Write header if sheet empty
    if ws.max_row == 1 and all(cell.value is None for cell in ws[1]):
        ws.delete_rows(1)
        ws.append(list(row.keys()))
    elif ws.max_row == 0:
        ws.append(list(row.keys()))
    ws.append([row.get(col.value, "") for col in ws[1]])
    wb.save(XLSX_PATH)


def record_proposal(proposal_text: str, submission_id: str | None) -> None:
    """Record a generated proposal and optional submission identifier."""
    row = {
        "timestamp": utc_now_iso(),
        "proposal_text": proposal_text,
        "submission_id": submission_id or "",
    }
    _append_row("Proposals", row)


def record_execution_result(
    status: str,
    block_hash: str,
    outcome: str,
    submission_id: str | None = None,
) -> None:
    """Append governor execution details to the ``ExecutionResults`` sheet."""
    row = {
        "timestamp": utc_now_iso(),
        "submission_id": submission_id or "",
        "status": status,
        "block_hash": block_hash,
        "outcome": outcome,
    }
    _append_row("ExecutionResults", row)


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
