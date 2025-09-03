"""Proposal drafting utilities."""
from __future__ import annotations

import json
import os
import re
from datetime import datetime
from typing import Any, Dict

from llm import ollama_api


def _json_default(value: Any) -> str:
    """Return a JSON-serialisable representation for ``value``.

    Currently only :class:`datetime.datetime` objects require special handling,
    which are converted to ISO 8601 strings. Any other non-serialisable type
    raises ``TypeError`` so issues are surfaced early.
    """

    if isinstance(value, datetime):
        return value.isoformat()
    raise TypeError(f"Object of type {value.__class__.__name__} "
                    "is not JSON serialisable")


def build_prompt(context: Dict[str, Any]) -> str:
    """Compose a single prompt for the LLM with all context JSON."""
    return (
        "You are an autonomous Polkadot governance agent. "
        "Using context derived from community chat, forum discussions, news "
        "reports, on-chain metrics and historical referenda, draft a concise "
        "OpenGov proposal for the 'Root' track. Reference these sources where "
        "relevant.\n\n"
        "Fill out the following template and return only the completed text:\n"
        "Title: <short heading>\n"
        "Rationale: <brief reasoning referencing sentiment, risks and prior votes>\n"
        "Action: <specific on-chain steps>\n"
        "Expected Impact: <anticipated network effects>\n\n"
        f"=== CONTEXT (JSON) ===\n{json.dumps(context, indent=2, default=_json_default)}\n"
        "======================\n"
        "Return ONLY the proposal text, no additional commentary."
    )


def postprocess_draft(text: str) -> str:
    """Strip preamble and validate mandatory section headings.

    Removes any introductory phrases appearing before the ``Title:`` heading and
    ensures all required headings (Title, Rationale, Action, Expected Impact)
    are present at the start of lines.
    """

    idx = text.lower().find("title:")
    if idx == -1:
        raise ValueError("Missing 'Title:' section")
    cleaned = text[idx:].lstrip()

    headings = ["Title:", "Rationale:", "Action:", "Expected Impact:"]
    for heading in headings:
        if not re.search(rf"^{heading}", cleaned, flags=re.MULTILINE):
            raise ValueError(f"Missing '{heading}' section")

    return cleaned


def draft(
    context_dict: Dict[str, Any],
    temperature: float | None = None,
    max_tokens: int | None = None,
    timeout: float | None = None,
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
    timeout = (
        timeout
        if timeout is not None
        else float(os.getenv("PROPOSAL_TIMEOUT", os.getenv("OLLAMA_TIMEOUT", "240")))
    )
    prompt = build_prompt(context_dict)
    raw = ollama_api.generate_completion(
        prompt=prompt,
        system="You are Polkadot-Gov-Agent v1.",
        model="gemma3:4b",
        temperature=temperature,
        max_tokens=max_tokens,
        timeout=timeout,
    )
    try:
        return postprocess_draft(raw)
    except ValueError:
        # If the model returns an unexpected format, fall back to the raw text
        # rather than raising and terminating the pipeline.
        return raw.strip()
