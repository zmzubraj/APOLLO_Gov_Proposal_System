"""
referenda_updater.py  – 2025-05-20 (JSON-first content)
----------------------------------
Appends every new Polkadot referenda to the
data/input/PKD Governance Data.xlsx workbook.

Content logic:
  1) Hit Subscan for metadata.
  2) Always try Subsquare JSON -> strip_html(detail.content).
  3) If JSON misses title only, fall back HTML <h1> for title.
  4) If JSON misses content, store "/" (No context).
  5) Stop only on real 404s, not on empty content.
"""

from __future__ import annotations
import csv, time, datetime as dt, pathlib, os, requests
from typing import List, Dict

import pandas as pd
from bs4 import BeautifulSoup
from substrateinterface import SubstrateInterface

from data_processing.data_loader import load_first_sheet
from data_processing.proposal_store import ensure_workbook
from utils.helpers import extract_json_safe, utc_now_iso

# ─────────────── Paths & Constants ────────────────────────────────────
ROOT = pathlib.Path(__file__).resolve().parents[2]
DATA_DIR = ROOT / "data"
XLSX_PATH = DATA_DIR / "input" / "PKD Governance Data.xlsx"
FAIL_CSV = DATA_DIR / "output" / "referenda_failures.csv"
FAIL_CSV.parent.mkdir(exist_ok=True, parents=True)

API_KEY = os.getenv("SUBSCAN_API_KEY", "")
SUBSCAN_URL = "https://polkadot.api.subscan.io/api/scan"
SUBSCAN_HDRS = {"Content-Type": "application/json", "X-API-Key": API_KEY}

SS_BASE = "https://polkadot.subsquare.io/referenda/{idx}"
SS_TIMEL = SS_BASE + "?tab=timeline"
SS_HDRS = {"User-Agent": "Mozilla/5.0 (compatible; DemoBot/0.1)"}

SUBSTRATE_RPC = "wss://rpc.polkadot.io"

COLS = [
    "Referendum_ID", "Title", "Content",
    "Start", "End", "Duration_days",
    "Participants", "ayes_amount", "nays_amount", "Total_Voted_DOT",
    "Eligible_DOT", "Not_Perticipated_DOT", "Voted_percentage",
    "Status",
]
NUMERIC_COLS = {
    "Duration_days", "Participants", "ayes_amount", "nays_amount",
    "Total_Voted_DOT", "Eligible_DOT", "Not_Perticipated_DOT", "Voted_percentage"
}

to_iso  = (
    lambda ts: dt.datetime.fromtimestamp(ts, dt.UTC).strftime("%Y-%m-%d %H:%M:%S")
    if ts
    else ""
)
strip_h = lambda h: BeautifulSoup(h, "html.parser").get_text(" ", strip=True)


# ───────────────────── Subscan helpers ─────────────────────────────────
def subscan_detail(idx: int) -> dict | None:
    try:
        r = requests.post(
            f"{SUBSCAN_URL}/referenda/referendum",
            headers=SUBSCAN_HDRS,
            json={"referendum_index": idx},
            timeout=12
        )
        if r.ok and r.json().get("code") == 0:
            return r.json()["data"]
    except:
        pass
    return None


def subscan_votes(idx: int) -> int:
    try:
        r = requests.post(
            f"{SUBSCAN_URL}/referenda/votes",
            headers=SUBSCAN_HDRS,
            json={"referendum_index": idx, "row": 1, "page": 0},
            timeout=8
        )
        if r.ok:
            return r.json().get("data", {}).get("count", 0)
    except:
        pass
    return 0


# ───────────────────── Subsquare JSON for content ─────────────────────
def fetch_ss_json(idx: int) -> dict | None:
    """Identical to Gether Content.py’s `fetch_json_from_timeline`."""
    for url in (SS_TIMEL, SS_BASE):
        try:
            resp = requests.get(url.format(idx=idx), headers=SS_HDRS, timeout=12)
            if not resp.ok:
                continue
            soup = BeautifulSoup(resp.text, "html.parser")
            tag = soup.find("script", id="__NEXT_DATA__")
            if not tag or not tag.string:
                continue
            data = extract_json_safe(tag.string)
            return data.get("props", {}).get("pageProps", {}).get("detail", {})
        except:
            continue
    return None


# ───────────────────── Issuance helper ─────────────────────────────────
_sub: SubstrateInterface | None = None


def issuance_at_block(block: int) -> float:
    global _sub
    if _sub is None:
        _sub = SubstrateInterface(url=SUBSTRATE_RPC, type_registry_preset="polkadot")
    return _sub.query("Balances", "TotalIssuance",
                      block_hash=_sub.get_block_hash(block)).value / 10 ** 10


# ───────────────────── Custom Exception ─────────────────────────────────
class IncompleteDataError(RuntimeError):
    def __init__(self, row, missing):
        super().__init__("incomplete data after fallback")
        self.row = row
        self.missing = missing


# ───────────────────── Collector ────────────────────────────────────────
def collect_referendum(idx: int) -> Dict[str, str | int | float]:
    missing: List[str] = []
    d = subscan_detail(idx) or {}

    # 1) Title / timeline from Subscan
    title = (d.get("title") or "").strip()
    status = d.get("status", "")
    start_ts = end_ts = None
    for ev in d.get("timeline", []):
        if ev["status"] == "Submitted": start_ts = ev["time"]
        if ev["status"] in ("Executed", "Rejected", "Timeout", "Cancelled", "Killed", "ExecutedFailed"):
            end_ts = ev["time"]

    # 2) JSON content from Subsquare (exactly as old script)
    content = "/"
    ss = fetch_ss_json(idx)
    if ss:
        raw = ss.get("content", "")
        content = strip_h(raw) if raw else "/"
        # JSON may also carry a title override
        title = title or (ss.get("title") or "").strip()
        # and sometimes the JSON has end-time too:
        if not end_ts:
            for ev in ss.get("onchainData", {}).get("timeline", []):
                if "Executed" in ev.get("name", ""):
                    end_ts = ev.get("indexer", {}).get("blockTime", 0) // 1000

    # 3) If title STILL missing → scrape plain HTML <h1> / <h2>
    if not title:
        try:
            resp = requests.get(SS_BASE.format(idx=idx), headers=SS_HDRS, timeout=8)
            soup = BeautifulSoup(resp.text, "html.parser")
            elt = soup.find("h1") or soup.find("h2")
            title = elt.get_text(" ", strip=True) if elt else "/"
        except:
            title = "/"

    # 4) Now we have Title + Content (never blank)
    #    If both came back as "/" and page 404’d above, treat as real gap:
    if title == "/" and content == "/" and subscan_detail(idx) is None:
        raise RuntimeError("gap (true 404)")

    # 5) Derived metrics (same as before)
    duration = (end_ts - start_ts) / 86400 if start_ts and end_ts else None
    participants = subscan_votes(idx)
    ayes = round(int(d.get("ayes_amount", 0)) / 10 ** 10, 4)
    nays = round(int(d.get("nays_amount", 0)) / 10 ** 10, 4)
    total = ayes + nays

    end_block = max(
        (ev["block"] for ev in d.get("timeline", [])
         if ev["status"] in ("Executed", "Rejected", "Timeout", "Cancelled", "Killed", "ExecutedFailed")),
        default=0
    )
    eligible = issuance_at_block(end_block) if end_block else 0
    notp = max(eligible - total, 0)
    pct = 100 * total / eligible if eligible else 0

    row = {
        "Referendum_ID": idx,
        "Title": title,
        "Content": content,
        "Start": to_iso(start_ts),
        "End": to_iso(end_ts),
        "Duration_days": round(duration, 2) if duration else 0,
        "Participants": participants,
        "ayes_amount": ayes,
        "nays_amount": nays,
        "Total_Voted_DOT": round(total, 4),
        "Eligible_DOT": round(eligible, 4),
        "Not_Perticipated_DOT": round(notp, 4),
        "Voted_percentage": round(pct, 4),
        "Status": status,
    }

    # 6) Fill any OTHER blanks / collect missing-info
    for c in COLS:
        if row[c] in (None, ""):
            missing.append(c)
            row[c] = 0 if c in NUMERIC_COLS else "/"

    if missing:
        raise IncompleteDataError(row, missing)

    return row


# ───────────────────── last stored id ──────────────────────────────────
def last_stored_id() -> int:
    if not XLSX_PATH.exists():
        return -1
    df = pd.read_excel(XLSX_PATH, sheet_name="Referenda")
    ids = pd.to_numeric(df.iloc[:, 0], errors="coerce").dropna()
    return int(ids.iloc[-1]) if not ids.empty else -1


# ───────────────────── Main updater ─────────────────────────────────────
def update_referenda(max_new: int = 500, max_gaps: int = 5) -> None:
    last = last_stored_id()
    print(f"Last Referendum_ID in workbook: {last}")

    df = (
        pd.read_excel(XLSX_PATH, sheet_name="Referenda")
        if XLSX_PATH.exists()
        else pd.DataFrame(columns=COLS)
    )
    failures: List[Dict[str, str]] = []
    attempted = gap_streak = 0
    next_id = last + 1

    while attempted < max_new and gap_streak < max_gaps:
        attempted += 1
        try:
            row = collect_referendum(next_id)
            df = pd.concat([df, pd.DataFrame([row])], ignore_index=True)
            # print(f"✅ {next_id}")
            gap_streak = 0

        except IncompleteDataError as inc:
            df = pd.concat([df, pd.DataFrame([inc.row])], ignore_index=True)

            key_missing = {"Start", "End", "Status"}
            if key_missing.issubset(set(inc.missing)):
                failures.append({
                    "Referendum_ID": next_id,
                    "error": str(inc),
                    "missing_info": ", ".join(inc.missing),
                    "function": "collect_referendum",
                    "time": utc_now_iso(),
                })
                # print(f"• {next_id} gap (missing Start,End,Status)")
                gap_streak += 1
            else:
                failures.append({
                    "Referendum_ID": next_id,
                    "error": str(inc),
                    "missing_info": ", ".join(inc.missing),
                    "function": "collect_referendum",
                    "time": utc_now_iso(),
                })
                # print(f"❌ {next_id} imputed {inc.missing}")
                gap_streak = 0

        except RuntimeError as gap_exc:
            # true 404 gap
            failures.append({
                "Referendum_ID": next_id,
                "error": str(gap_exc),
                "missing_info": "",
                "function": "collect_referendum",
                "time": utc_now_iso(),
            })
            # print(f"• {next_id} {gap_exc}")
            gap_streak += 1

        except Exception as e:
            failures.append({
                "Referendum_ID": next_id,
                "error": str(e),
                "missing_info": "",
                "function": "collect_referendum",
                "time": utc_now_iso(),
            })
            print(f"❌ {next_id} unexpected {e}")
            gap_streak += 1

        next_id += 1
        time.sleep(0.25)

    # persist results
    print(f"Stopped after {attempted} attempts (gaps {gap_streak}/{max_gaps}).")
    if ensure_workbook() is None:
        return
    with pd.ExcelWriter(
        XLSX_PATH, engine="openpyxl", mode="a", if_sheet_exists="replace"
    ) as writer:
        df.to_excel(writer, sheet_name="Referenda", index=False)
    print(f"✔ Workbook updated → {XLSX_PATH}")

    if failures:
        with open(FAIL_CSV, "a", newline="", encoding="utf-8") as f:
            w = csv.DictWriter(f, fieldnames=failures[0].keys())
            if f.tell() == 0: w.writeheader()
            w.writerows(failures)
        print(f"⚠ Logged {len(failures)} failures → {FAIL_CSV}")


# ───────────────────── Single append/reconcile helpers ──────────────────

def append_referendum(idx: int) -> None:
    """Fetch ``idx`` and append or update its row in the Referenda sheet."""

    df = (
        pd.read_excel(XLSX_PATH, sheet_name="Referenda")
        if XLSX_PATH.exists()
        else pd.DataFrame(columns=COLS)
    )
    try:
        row = collect_referendum(idx)
    except Exception:
        return

    row_df = pd.DataFrame([row], columns=COLS)
    if not df.empty and "Referendum_ID" in df.columns and idx in df["Referendum_ID"].values:
        df.loc[df["Referendum_ID"] == idx, :] = row_df.values
    else:
        df = pd.concat([df, row_df], ignore_index=True)

    with pd.ExcelWriter(
        XLSX_PATH, engine="openpyxl", mode="a", if_sheet_exists="replace"
    ) as writer:
        df.to_excel(writer, sheet_name="Referenda", index=False)


def reconcile_referenda(ids: list[int] | None = None) -> None:
    """Refresh stored rows from on-chain data."""

    if not XLSX_PATH.exists():
        return
    df = pd.read_excel(XLSX_PATH, sheet_name="Referenda")
    if df.empty or "Referendum_ID" not in df.columns:
        return

    refresh_ids = ids or df["Referendum_ID"].dropna().astype(int).tolist()
    for rid in refresh_ids:
        try:
            row = collect_referendum(rid)
            row_df = pd.DataFrame([row], columns=df.columns)
            df.loc[df["Referendum_ID"] == rid, :] = row_df.values
        except Exception:
            continue

    with pd.ExcelWriter(
        XLSX_PATH, engine="openpyxl", mode="a", if_sheet_exists="replace"
    ) as writer:
        df.to_excel(writer, sheet_name="Referenda", index=False)


if __name__ == "__main__":
    update_referenda()
