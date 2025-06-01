"""
governance_analysis.py  (revised for new columns)
-------------------------------------------------
KPIs mined from columns that actually exist in
'PKD Governance Data.xlsx'.

Columns detected:
- Referendum_ID
- Title
- Start, End
- Duration_days
- Participants
- ayes_amount, nays_amount
- Total_Voted_DOT
- Eligible_DOT
- Voted_percentage      # e.g. 0.209305  ≈ 0.21 %
- Status                # Executed / Rejected / Cancelled …

Feel free to tweak KPI formulas after inspecting your data.
"""

from __future__ import annotations
from typing import Dict, Any
import datetime as dt
from collections import Counter
import numpy as np
import pandas as pd
import re

from src.data_processing.data_loader import load_first_sheet
from src.llm.ollama_api import generate_completion


# ────────────────────────────────────────────────────────────────────────────
# Helpers
# ────────────────────────────────────────────────────────────────────────────
def _prep_df(df: pd.DataFrame) -> pd.DataFrame:
    df = df.copy()
    df["Title"] = df["Title"].fillna("")

    # Parse dates
    df["Start"] = pd.to_datetime(df["Start"], errors="coerce")
    df["End"] = pd.to_datetime(df["End"], errors="coerce")
    # Ensure numeric
    num_cols = [
        "Duration_days",
        "Participants",
        "ayes_amount",
        "nays_amount",
        "Total_Voted_DOT",
        "Eligible_DOT",
        "Voted_percentage",
    ]
    for c in num_cols:
        df[c] = pd.to_numeric(df[c], errors="coerce")
    return df


def top_keywords(titles: pd.Series, k: int = 10) -> list[str]:
    """
    Extract the k most common non-stop-words (≥3 letters) from the Title column.
    Gracefully skips NaN or non-string cells.
    """
    stop = set("the of a to and in for on with by is are be at".split())
    # Drop NaN, cast to str, lower-case
    corpus = " ".join(map(str, titles.dropna().astype(str))).lower()
    words = re.findall(r"\b[a-z]{3,}\b", corpus)
    freq = Counter(w for w in words if w not in stop)
    return [w for w, _ in freq.most_common(k)]


# ────────────────────────────────────────────────────────────────────────────
# KPI computation
# ────────────────────────────────────────────────────────────────────────────
def build_kpi_dict(df: pd.DataFrame) -> Dict[str, Any]:
    executed = df[df["Status"].str.lower() == "executed"]
    rejected = df[df["Status"].str.lower() == "rejected"]

    kpis: Dict[str, Any] = {
        "total_referenda": len(df),
        "executed_pct": round(len(executed) / len(df) * 100, 1) if len(df) else 0,
        "rejected_pct": round(len(rejected) / len(df) * 100, 1) if len(df) else 0,
        "avg_turnout_pct": round(df["Voted_percentage"].mean(), 2),
        "median_turnout_pct": round(df["Voted_percentage"].median(), 2),
        "avg_participants": int(df["Participants"].mean()),
        "avg_duration_days": round(df["Duration_days"].mean(), 2),
        # Monthly submission trend (last 6 months)
        "monthly_counts": (
            df.groupby(df["Start"].dt.strftime("%Y-%m"))["Referendum_ID"]
            .count()
            .tail(6)
            .to_dict()
        ),
        "top_keywords": top_keywords(df["Title"]),
    }
    return kpis


# ────────────────────────────────────────────────────────────────────────────
# Public function
# ────────────────────────────────────────────────────────────────────────────
def get_governance_insights(as_narrative: bool = False, model: str | None = None) -> Dict[str, Any]:
    df_raw = load_first_sheet()
    df = _prep_df(df_raw)

    kpis = build_kpi_dict(df)

    if as_narrative:
        prompt = (
            "Summarise the following Polkadot governance KPIs in <=120 words, "
            "highlighting voter engagement and any worrying trends.\n\n"
            f"{kpis}"
        )
        kpis["insight_summary"] = generate_completion(
            prompt=prompt,
            system="You are a Polkadot governance analyst.",
            model="gemma3:4b",
            temperature=0.2,
            max_tokens=160,
        ).strip()

    return kpis


# ────────────────────────────────────────────────────────────────────────────
# Manual test
# ────────────────────────────────────────────────────────────────────────────
if __name__ == "__main__":
    import pprint, json, pathlib

    insights = get_governance_insights(as_narrative=True)
    pprint.pprint(insights)

    out = pathlib.Path(__file__).resolve().parents[2] / "data" / "output"
    out.mkdir(parents=True, exist_ok=True)
    (out / "governance_kpis.json").write_text(json.dumps(insights, indent=2))
    print(f"KPIs saved → {out/'governance_kpis.json'}")
