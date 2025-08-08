"""Utilities for interacting with the Polkadot OpenGov governor.

This module wraps a handful of helper functions used by the execution
layer of the agent.  They establish Substrate connections, submit and
query proposals and, newly, provide ``await_execution`` which polls the
chain for the final outcome of a referendum.
"""
from __future__ import annotations

import time
from typing import Any, Dict, Iterable, Optional, Union


def connect(node_url: str):
    """Return a ``SubstrateInterface`` connection to ``node_url``.

    Parameters
    ----------
    node_url: str
        WebSocket/HTTP endpoint of the Substrate node.
    """
    from substrateinterface import SubstrateInterface  # local import for testability

    return SubstrateInterface(url=node_url)


def _create_keypair(private_key: str):
    """Create a ``Keypair`` from a raw private key."""
    from substrateinterface import Keypair  # local import for testability

    return Keypair.create_from_private_key(private_key)


def _tracks(substrate: Any) -> Dict[int, Dict[str, Any]]:
    """Return mapping of track id -> info."""
    tracks = substrate.get_constant("Referenda", "Tracks")
    # Chain constants may be list of tuples; normalise to dict
    if isinstance(tracks, dict):
        return tracks
    result: Dict[int, Dict[str, Any]] = {}
    if isinstance(tracks, Iterable):
        for item in tracks:
            if isinstance(item, (tuple, list)) and len(item) == 2:
                result[int(item[0])] = item[1]
    return result


def resolve_track(substrate: Any, track: Union[str, int]) -> int:
    """Return numeric track id for ``track`` which may be name or id."""
    if isinstance(track, int):
        return track
    tracks = _tracks(substrate)
    for tid, info in tracks.items():
        name = info.get("name") or info.get("Name") or info.get("track")
        if name == track:
            return int(tid)
    raise ValueError(f"Unknown track: {track}")


def required_deposit(substrate: Any, track_id: int) -> int:
    """Return the decision deposit required for ``track_id``."""
    info = _tracks(substrate).get(track_id, {})
    deposit = info.get("decision_deposit") or info.get("decisionDeposit")
    if deposit is None:
        return 0
    try:
        return int(deposit)
    except Exception:
        return 0


def _extract_event(receipt: Any, module: str, event: str) -> Optional[Any]:
    events = getattr(receipt, "triggered_events", []) or []
    for e in events:
        mod = getattr(e, "event_module", getattr(getattr(e, "event", {}), "module", ""))
        name = getattr(e, "event_name", getattr(getattr(e, "event", {}), "event", ""))
        if mod == module and name == event:
            return e
    return None


def submit_preimage(node_url: str, private_key: str, preimage: bytes) -> Dict[str, Any]:
    """Submit a preimage to the chain and return receipt details."""
    substrate = connect(node_url)
    keypair = _create_keypair(private_key)
    call = substrate.compose_call(
        call_module="Preimage",
        call_function="note_preimage",
        call_params={"bytes": preimage},
    )
    extrinsic = substrate.create_signed_extrinsic(call=call, keypair=keypair)
    receipt = substrate.submit_extrinsic(extrinsic, wait_for_inclusion=True)
    result = parse_receipt(receipt)
    event = _extract_event(receipt, "Preimage", "Noted")
    if event is not None:
        params = getattr(event, "params", [])
        if params:
            hash_val = params[0].get("value") if isinstance(params[0], dict) else getattr(params[0], "value", None)
            result["preimage_hash"] = hash_val
    return result


def submit_proposal(
    node_url: str,
    private_key: str,
    preimage_hash: str,
    track: Union[str, int],
    value: Optional[int] = None,
) -> Dict[str, Any]:
    """Submit a referendum proposal referencing an existing preimage.

    Parameters
    ----------
    node_url, private_key, preimage_hash: see :func:`submit_preimage`.
    track: Union[str, int]
        Track identifier or human-readable name.
    value: Optional[int]
        Deposit to attach. If omitted the chain's required decision deposit
        for the given track is used.
    """
    substrate = connect(node_url)
    keypair = _create_keypair(private_key)
    track_id = resolve_track(substrate, track)
    deposit = value if value is not None else required_deposit(substrate, track_id)
    call = substrate.compose_call(
        call_module="Referenda",
        call_function="submit",
        call_params={
            "proposal": preimage_hash,
            "track": track_id,
            "value": deposit,
        },
    )
    extrinsic = substrate.create_signed_extrinsic(call=call, keypair=keypair)
    receipt = substrate.submit_extrinsic(extrinsic, wait_for_inclusion=True)
    result = parse_receipt(receipt)
    event = _extract_event(receipt, "Referenda", "Submitted")
    if event is not None:
        params = getattr(event, "params", [])
        if params:
            idx = params[0].get("value") if isinstance(params[0], dict) else getattr(params[0], "value", None)
            result["referendum_index"] = idx
    return result


def query_proposal_status(node_url: str, referendum_index: int) -> Optional[str]:
    """Return a simple status string for ``referendum_index`` or ``None``."""
    substrate = connect(node_url)
    info = substrate.query(
        module="Referenda", storage_function="ReferendumInfoFor", params=[referendum_index]
    )
    value = getattr(info, "value", None)
    if not value:
        return None
    if isinstance(value, dict):
        if "Ongoing" in value:
            return value["Ongoing"].get("status")
        if "Approved" in value:
            return "Approved"
        if "Rejected" in value:
            return "Rejected"
        if "Cancelled" in value:
            return "Cancelled"
    return str(value)


def parse_receipt(receipt: Any) -> Dict[str, Any]:
    """Convert a substrate receipt into a simple dictionary."""
    return {
        "extrinsic_hash": getattr(receipt, "extrinsic_hash", None),
        "block_hash": getattr(receipt, "block_hash", None),
        "is_success": getattr(receipt, "is_success", False),
        "error_message": getattr(receipt, "error_message", None),
    }


def await_execution(
    node_url: str,
    referendum_index: int,
    submission_id: str,
    poll_interval: float = 6.0,
    max_attempts: int = 60,
) -> tuple[str, str]:
    """Poll for the final referendum outcome.

    Parameters
    ----------
    node_url:
        Endpoint of the Substrate node.
    referendum_index:
        Index of the referendum to poll.
    submission_id:
        Identifier returned when the proposal was submitted.  Currently
        unused but retained for logging/compatibility.
    poll_interval:
        Seconds to wait between polls.
    max_attempts:
        Maximum number of polling attempts before timing out.

    Returns
    -------
    tuple[str, str]
        ``(block_hash, outcome)`` where ``outcome`` is the final status
        such as ``"Approved"`` or ``"Rejected"``.  If the outcome could
        not be determined a ``("", "timeout")`` tuple is returned.
    """

    substrate = connect(node_url)
    for _ in range(max_attempts):
        status = query_proposal_status(node_url, referendum_index)
        if status and status not in {"Ongoing", "Deciding"}:
            block_hash = substrate.get_block_hash() or ""
            return block_hash, status
        time.sleep(poll_interval)
    return "", "timeout"

