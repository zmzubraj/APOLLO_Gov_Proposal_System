"""Proposal submission utilities."""
from __future__ import annotations

import os
from typing import Dict, Any, Optional

import requests


def _env_credentials() -> Dict[str, Any]:
    """Collect submission credentials from environment variables."""
    return {
        "platform": os.getenv("PROPOSAL_PLATFORM", "snapshot"),
        "api_url": os.getenv("SNAPSHOT_API_URL"),
        "api_key": os.getenv("SNAPSHOT_API_KEY"),
        "node_url": os.getenv("SUBSTRATE_NODE_URL"),
        "private_key": os.getenv("SUBSTRATE_PRIVATE_KEY"),
    }


def submit_proposal(
    proposal_text: str, credentials: Optional[Dict[str, Any]] = None
) -> Optional[str]:
    """Submit a proposal to a governance platform.

    Parameters
    ----------
    proposal_text: str
        The body of the proposal to submit.
    credentials: dict, optional
        Authentication and target information. If omitted, values are read
        from environment variables.

    Returns
    -------
    Optional[str]
        Identifier returned by the platform, such as transaction hash or URL,
        or ``None`` if submission fails.
    """
    creds = credentials or _env_credentials()
    platform = creds.get("platform", "snapshot")

    try:
        if platform == "snapshot":
            api_url = creds.get("api_url")
            if not api_url:
                raise ValueError("'api_url' missing for snapshot submission")
            headers = {}
            api_key = creds.get("api_key")
            if api_key:
                headers["Authorization"] = f"Bearer {api_key}"
            payload = {"proposal": proposal_text}
            response = requests.post(api_url, json=payload, headers=headers, timeout=10)
            response.raise_for_status()
            data = response.json()
            return data.get("tx_hash") or data.get("url") or data.get("id")

        if platform == "substrate":
            from substrateinterface import SubstrateInterface, Keypair

            node_url = creds.get("node_url")
            private_key = creds.get("private_key")
            if not (node_url and private_key):
                raise ValueError(
                    "'node_url' and 'private_key' required for substrate submission"
                )
            substrate = SubstrateInterface(url=node_url)
            keypair = Keypair.create_from_private_key(private_key)
            call = substrate.compose_call(
                call_module=creds.get("call_module", "Referenda"),
                call_function=creds.get("call_function", "submit"),
                call_params=creds.get("call_params", {"proposal": proposal_text}),
            )
            extrinsic = substrate.create_signed_extrinsic(call=call, keypair=keypair)
            receipt = substrate.submit_extrinsic(extrinsic, wait_for_inclusion=True)
            return receipt.extrinsic_hash
    except Exception:
        return None

    return None
