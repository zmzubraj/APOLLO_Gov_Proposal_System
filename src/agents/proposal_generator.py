"""Proposal drafting utilities."""
from __future__ import annotations

import json
import os
from typing import Dict, Any

from llm import ollama_api


def build_prompt(context: Dict[str, Any]) -> str:
    """Compose a single prompt for the LLM with all context JSON."""
    return (
        "You are an autonomous Polkadot governance agent. "
        "Draft a concise OpenGov proposal that (1) addresses current community "
        "sentiment and risks, (2) references recent on-chain activity, "
        "(3) aligns with historical governance patterns, and "
        "(4) is formatted for the 'Root' track including Title, Rationale, Action, "
        "and Expected Impact sections.\n\n"
        f"=== CONTEXT (JSON) ===\n{json.dumps(context, indent=2)}\n"
        "======================\n"
        "Return ONLY the proposal text, no JSON."
    )


def draft(
    context_dict: Dict[str, Any],
    temperature: float | None = None,
    max_tokens: int | None = None,
) -> str:
    """Return a proposal generated from ``context_dict``.

    ``temperature`` and ``max_tokens`` default to the environment variables
    ``PROPOSAL_TEMPERATURE`` and ``PROPOSAL_MAX_TOKENS`` (falling back to 0.3 and
    4096 respectively).
    """
    temperature = (
        temperature
        if temperature is not None
        else float(os.getenv("PROPOSAL_TEMPERATURE", "0.3"))
    )
    max_tokens = (
        max_tokens
        if max_tokens is not None
        else int(os.getenv("PROPOSAL_MAX_TOKENS", "4096"))
    )
    prompt = build_prompt(context_dict)
    return ollama_api.generate_completion(
        prompt=prompt,
        system="You are Polkadot-Gov-Agent v1.",
        model="gemma3:4b",
        temperature=temperature,
        max_tokens=max_tokens,
    )
