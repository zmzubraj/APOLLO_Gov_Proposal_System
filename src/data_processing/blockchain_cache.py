"""
blockchain_cache.py
-------------------
Smart on-chain data cache for the last 3 days of Polkadot blocks.

Behaviour
---------
1. If `blocks_last3days.json` is absent  → fetch & save.
2. If present:
   • If newest block > 3 days old       → delete file, fetch fresh.
   • Else if cache is ≤2 blocks behind  → reuse.
   • Else                              → refresh and overwrite.
"""

from __future__ import annotations

import datetime as dt
import json
import pathlib
from typing import List, Dict, Any

from substrateinterface import SubstrateInterface

from data_processing.blockchain_data_fetcher import fetch_recent_blocks

# ---------------------------------------------------------------------------
PROJECT_ROOT = pathlib.Path(__file__).resolve().parents[2]  # data_processing/..
CACHE_FILE = PROJECT_ROOT / "data" / "output" / "blocks_last3days.json"

MAX_BLOCK_LAG = 2  # considered fresh if within 2 blocks of chain head
MAX_AGE_DAYS = 1  # purge if newest cached block older than 1 days

SUBSTRATE_RPC = "wss://rpc.polkadot.io"


# ───────────────── helpers ────────────────────────────────────────────────
def _chain_latest_blocknum() -> int:
    sb = SubstrateInterface(url=SUBSTRATE_RPC, type_registry_preset="polkadot")
    return sb.get_block_number(sb.get_chain_head())


def _cache_latest_blocknum(blocks: List[Dict[str, Any]]) -> int:
    return max(b["block_num"] for b in blocks) if blocks else 0


def _cache_latest_timestamp(blocks: List[Dict[str, Any]]) -> int:
    return max(b["block_timestamp"] for b in blocks) if blocks else 0


def _is_too_old(blocks: List[Dict[str, Any]]) -> bool:
    age_days = (
        dt.datetime.now(dt.UTC)
        - dt.datetime.fromtimestamp(_cache_latest_timestamp(blocks), dt.UTC)
    ).days
    return age_days > MAX_AGE_DAYS


# ───────────────── public API ─────────────────────────────────────────────
def get_recent_blocks_cached() -> List[Dict[str, Any]]:
    """Return fresh list of last-3-day blocks, refreshing the cache if needed."""
    refresh_needed = True
    blocks: List[Dict[str, Any]] = []

    if CACHE_FILE.exists():
        try:
            blocks = json.loads(CACHE_FILE.read_text())
            if _is_too_old(blocks):
                print("🗑️  Cached block data older than 3 days – refreshing …")
            else:
                chain_latest = _chain_latest_blocknum()
                cache_latest = _cache_latest_blocknum(blocks)
                if chain_latest - cache_latest <= MAX_BLOCK_LAG:
                    print("✅ Block cache is fresh – using cached data.")
                    refresh_needed = False
                else:
                    print("♻️  Cache behind chain head – refreshing …")
        except Exception as e:
            print(f"⚠️  Cache unreadable ({e}) – rebuilding …")

    if refresh_needed:
        blocks, _ = fetch_recent_blocks()
        CACHE_FILE.parent.mkdir(parents=True, exist_ok=True)
        CACHE_FILE.write_text(json.dumps(blocks, indent=2))

    return blocks


# CLI smoke-test -----------------------------------------------------------
if __name__ == "__main__":
    blks = get_recent_blocks_cached()
    print(f"Blocks fetched: {len(blks)}")