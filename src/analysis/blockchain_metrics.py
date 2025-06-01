"""
blockchain_metrics.py
---------------------
Convert raw block details (from blockchain_data_fetcher.fetch_recent_blocks)
into easy-to-digest KPIs for the last three UTC days.

KPIs produced
=============
• daily_tx_count           {YYYY-MM-DD: int}
• daily_total_fees_DOT     {date: float}
• avg_tx_per_block         float
• avg_fee_per_tx_DOT       float
• busiest_hour_utc         "YYYY-MM-DD HH:00"
"""

from __future__ import annotations

import datetime as dt
import json
import pathlib
from collections import defaultdict, Counter
from typing import List, Dict, Any

from src.utils.helpers import abbrev_number


# ---------------------------------------------------------------------------
# Public entry
# ---------------------------------------------------------------------------
def summarise_blocks(blocks: List[Dict[str, Any]]) -> Dict[str, Any]:
    if not blocks:
        return {
            "daily_tx_count": {},
            "daily_total_fees_DOT": {},
            "avg_tx_per_block": 0,
            "avg_fee_per_tx_DOT": 0,
            "busiest_hour_utc": "",
        }

    daily_txs: dict[str, int] = defaultdict(int)
    daily_fees: dict[str, float] = defaultdict(float)
    hourly_counter: Counter[str] = Counter()

    total_tx, total_fee, n_blocks = 0, 0.0, 0

    for blk in blocks:
        ts = dt.datetime.utcfromtimestamp(blk["block_timestamp"])
        day = ts.strftime("%Y-%m-%d")
        hour_key = ts.strftime("%Y-%m-%d %H:00")

        txs = blk.get("extrinsics_count", 0)
        fee = float(blk.get("total_fee", 0)) / 10**10  # planck → DOT

        daily_txs[day] += txs
        daily_fees[day] += fee
        hourly_counter[hour_key] += txs

        total_tx += txs
        total_fee += fee
        n_blocks += 1

    avg_tx_per_block = round(total_tx / n_blocks, 2)
    avg_fee_per_tx = round(total_fee / max(total_tx, 1), 6)

    busiest_hour = hourly_counter.most_common(1)[0][0]

    return {
        "daily_tx_count": dict(daily_txs),
        "daily_total_fees_DOT": {d: round(f, 3) for d, f in daily_fees.items()},
        "avg_tx_per_block": avg_tx_per_block,
        "avg_fee_per_tx_DOT": avg_fee_per_tx,
        "busiest_hour_utc": busiest_hour,
    }


# ---------------------------------------------------------------------------
# Convenience: load JSON dumped by blockchain_data_fetcher test-run
# ---------------------------------------------------------------------------
def load_blocks_from_file(path: str | pathlib.Path) -> List[Dict[str, Any]]:
    with open(path, "r", encoding="utf-8") as f:
        return json.load(f)


# ---------------------------------------------------------------------------
# CLI smoke-test
# ---------------------------------------------------------------------------
if __name__ == "__main__":
    default_json = pathlib.Path(__file__).resolve().parents[2] / "data" / "output" / "blocks_last3days.json"
    if not default_json.exists():
        print("Raw block file not found. Run blockchain_data_fetcher first.")
    else:
        blks = load_blocks_from_file(default_json)
        metrics = summarise_blocks(blks)
        from pprint import pprint

        pprint(metrics)

        print("\nPretty:")
        for d, tx in metrics["daily_tx_count"].items():
            fee = metrics["daily_total_fees_DOT"][d]
            print(f"• {d}: {tx:,} txs, {abbrev_number(fee, ' DOT')} fees")

