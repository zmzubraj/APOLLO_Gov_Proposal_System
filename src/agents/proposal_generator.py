"""Proposal drafting utilities."""
from __future__ import annotations

import json
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


def draft(context_dict: Dict[str, Any]) -> str:
    """Return a proposal generated from ``context_dict``."""
    prompt = build_prompt(context_dict)
    return ollama_api.generate_completion(
        prompt=prompt,
        system="You are Polkadot-Gov-Agent v1.",
        model="gemma3:4b",
        temperature=0.3,
        max_tokens=2048,
    )
