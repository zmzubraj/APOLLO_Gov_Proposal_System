"""
blockchain_data_fetcher.py
--------------------------
Collect detailed Polkadot block data for the last `LOOKBACK_DAYS`
via Subscan + on-chain timestamps.

• Requires env var SUBSCAN_API_KEY (or edit DEFAULT_API_KEY).
• Uses SubstrateInterface only to get block timestamps quickly.
• Aggregates basic metrics (tx count + fee) per UTC day.
"""

from __future__ import annotations
import os
import datetime as dt
from typing import List, Dict, Any, Tuple

import requests
from substrateinterface import SubstrateInterface

# ────────────────────────────────────────────────────────────────────────────
# Config
# ────────────────────────────────────────────────────────────────────────────
LOOKBACK_DAYS = 0.01

DEFAULT_API_KEY = "d90abfa9fe494603860086ea96628b8d"  # ← replace or use env
API_KEY = os.getenv("SUBSCAN_API_KEY", DEFAULT_API_KEY)

BASE_URL = "https://polkadot.api.subscan.io/api/scan"
HEADERS = {
    "Content-Type": "application/json",
    "X-API-Key": API_KEY,
}

SUBSTRATE_RPC = "wss://rpc.polkadot.io"


# ────────────────────────────────────────────────────────────────────────────
# Helper: fetch block timestamp
# ────────────────────────────────────────────────────────────────────────────
def _get_block_timestamp(substrate: SubstrateInterface, block_num: int) -> int:
    """
    Return Unix timestamp (seconds) for the given block.
    """
    block_hash = substrate.get_block_hash(block_num)
    if block_hash is None:          # defensive
        raise ValueError(f"Cannot find block hash for #{block_num}")
    # Query storage Timestamp.Now at that block
    ts_ms = substrate.query(
        module="Timestamp",
        storage_function="Now",
        block_hash=block_hash,
    ).value
    return ts_ms // 1000            # convert ms → s


# ────────────────────────────────────────────────────────────────────────────
# Main collector
# ────────────────────────────────────────────────────────────────────────────
def fetch_recent_blocks() -> Tuple[List[Dict[str, Any]], Dict[str, Dict[str, Any]]]:
    """
    Return
    ------
    blocks   : list[dict]  raw Subscan block details
    per_day  : dict[YYYY-MM-DD] → {"txs": int, "fee": float}
    """
    substrate = SubstrateInterface(url=SUBSTRATE_RPC, type_registry_preset="polkadot")

    latest = substrate.get_block_number(substrate.get_chain_head())
    chain_now_ts = _get_block_timestamp(substrate, latest)
    cutoff_ts = int(chain_now_ts - LOOKBACK_DAYS * 24 * 3600)

    blocks: list[dict] = []
    per_day: dict[str, dict[str, Any]] = {}
    n_calls = 0

    print(f"Starting from block {latest} - Time: {dt.datetime.utcfromtimestamp(chain_now_ts)}, looking back to UTC {dt.datetime.utcfromtimestamp(cutoff_ts)}")
    for num in range(latest, 0, -1):
        ts = _get_block_timestamp(substrate, num)
        if ts < cutoff_ts:
            break  # we’re past the window

        # ------------------------------------------------------------------
        # Call Subscan for detailed info
        # ------------------------------------------------------------------
        resp = requests.post(
            f"{BASE_URL}/block",
            headers=HEADERS,
            json={"block_num": num},
            timeout=10,
        )
        n_calls += 1
        if resp.status_code != 200:
            print(f"Subscan error on block {num}: {resp.text}")
            continue

        data = resp.json().get("data", {})
        blocks.append(data)

        # Aggregate
        day = dt.datetime.utcfromtimestamp(ts).strftime("%Y-%m-%d")
        per_day.setdefault(day, {"txs": 0, "fee": 0.0})
        per_day[day]["txs"] += data.get("extrinsics_count", 0)
        per_day[day]["fee"] += float(data.get("total_fee", 0)) / 10**10  # plancks→DOT

        # throttle – Subscan free tier is ~10 req/s, stay safe
        if n_calls % 10 == 0:
            import time

            time.sleep(1)

    print(f"Fetched {len(blocks)} blocks covering {len(per_day)} UTC days.")
    return blocks, per_day


# ────────────────────────────────────────────────────────────────────────────
# Stand-alone test
# ────────────────────────────────────────────────────────────────────────────
if __name__ == "__main__":
    blks, stats = fetch_recent_blocks()
    import json, pprint, pathlib

    # Pretty-print summary
    pprint.pprint(stats)

    # Optionally dump raw blocks to data/output
    out_dir = pathlib.Path(__file__).resolve().parents[2] / "data" / "output"
    out_dir.mkdir(parents=True, exist_ok=True)
    (out_dir / "blocks_last3days.json").write_text(json.dumps(blks, indent=2))
    print(f"Saved raw block data → {out_dir/'blocks_last3days.json'}")

