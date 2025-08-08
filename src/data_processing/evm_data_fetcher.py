"""Utility for fetching block and transaction data from an EVM chain."""
from __future__ import annotations

from typing import Any, Dict, List, Optional

from web3 import Web3

DEFAULT_RPC_URL = "http://localhost:8545"


def _to_hex(value: Any) -> Any:
    """Return hex string for bytes-like ``value``.

    Web3 often returns bytes for hashes. Converting them makes the data JSON
    serialisable and easier to test.
    """
    if isinstance(value, (bytes, bytearray)):
        return "0x" + value.hex()
    return value


def fetch_evm_blocks(
    rpc_url: str = DEFAULT_RPC_URL,
    start_block: Optional[int] = None,
    end_block: Optional[int] = None,
) -> List[Dict[str, Any]]:
    """Fetch blocks and full transaction data from an EVM compatible chain.

    Parameters
    ----------
    rpc_url: str
        HTTP RPC endpoint for the chain.
    start_block: int, optional
        First block number to fetch. Defaults to ``end_block - 4``.
    end_block: int, optional
        Last block number to fetch. Defaults to the chain head.
    """
    w3 = Web3(Web3.HTTPProvider(rpc_url))

    latest = w3.eth.block_number
    end = latest if end_block is None else end_block
    start = max(0, end - 4) if start_block is None else start_block

    blocks: List[Dict[str, Any]] = []
    for num in range(start, end + 1):
        block = w3.eth.get_block(num, full_transactions=True)
        txs = []
        for tx in block.get("transactions", []):
            txs.append(
                {
                    "hash": _to_hex(tx.get("hash")),
                    "from": tx.get("from"),
                    "to": tx.get("to"),
                    "value": tx.get("value"),
                }
            )
        blocks.append(
            {
                "number": block.get("number"),
                "hash": _to_hex(block.get("hash")),
                "timestamp": block.get("timestamp"),
                "transactions": txs,
            }
        )
    return blocks
