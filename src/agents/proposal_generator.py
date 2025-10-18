"""Proposal drafting utilities."""
from __future__ import annotations

import json
import os
import re
from datetime import datetime
from typing import Any, Dict

from llm import ollama_api


def _fallback_title(context: Dict[str, Any], source_name: str) -> str:
    topics = context.get("trending_topics") or []
    if topics:
        lead = ", ".join(str(t) for t in topics[:3])
        return f"Root Track Proposal: {lead}"
    sent = context.get("sentiment", {})
    label = sent.get("sentiment") if isinstance(sent, dict := sent) else ""
    label = label or "Community Priorities and Ecosystem Support"
    return f"Root Track Proposal: {label}"


def _fallback_section(text: str, default: str) -> str:
    text = str(text or "").strip()
    return text if text else default


def fallback_draft(context: Dict[str, Any], source_name: str) -> str:
    """Return a minimal, well-structured proposal when LLM drafting fails.

    The fallback composes sections from available context so the CLI always
    displays a usable proposal. Sections follow the same format enforced by
    postprocess_draft().
    """

    title = _fallback_title(context, source_name)

    sent = context.get("sentiment", {}) if isinstance(context.get("sentiment"), dict) else {}
    kb_summary = str(context.get("kb_summary") or "")
    gov = context.get("governance_kpis", {}) if isinstance(context.get("governance_kpis"), dict) else {}
    chain = context.get("chain_kpis", {}) if isinstance(context.get("chain_kpis"), dict) else {}

    sent_label = sent.get("sentiment") or "Mixed"
    sent_score = sent.get("sentiment_score")
    if isinstance(sent_score, (int, float)):
        sent_phrase = f"(score {sent_score:+.2f})"
    else:
        sent_phrase = ""

    rationale_default = (
        "Community sentiment is "
        f"{sent_label} {sent_phrase}. "
        "This proposal consolidates recent discussions, forum insights, and "
        "on-chain KPIs to improve participation and ecosystem outcomes. "
        + ("\n" + kb_summary[:450] if kb_summary else "")
    ).strip()
    rationale = _fallback_section(kb_summary, rationale_default)

    action_parts = []
    if chain:
        action_parts.append("Track relevant on-chain metrics and publish weekly updates.")
    if gov:
        action_parts.append("Coordinate with OpenGov tracks to align milestones and reporting.")
    action_parts.append("Define clear deliverables, timelines, and accountability.")
    action = " ".join(action_parts)

    impact = (
        "Higher voter turnout and transparency; better alignment of funding with "
        "community priorities; clearer progress visibility for stakeholders."
    )

    text = (
        f"Title: {title}\n"
        f"Rationale: {rationale}\n"
        f"Action: {action}\n"
        f"Expected Impact: {impact}"
    )
    return text


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


def build_prompt(context: Dict[str, Any], source_name: str) -> str:
    """Compose a single prompt for the LLM with all context JSON."""
    include_topics = os.getenv("PROPOSAL_INCLUDE_TOPICS", "0").lower() not in (
        "0",
        "false",
        "no",
    )
    topics_section = ""
    if include_topics:
        topics = context.get("trending_topics", [])
        if topics:
            bullet_list = "\n".join(f"- {topic}" for topic in topics)
            topics_section = f"Trending Topics:\n{bullet_list}\n\n"
    return (
        "You are an autonomous Polkadot governance agent. "
        f"Using context derived from {source_name}. Reference these sources where relevant.\n"
        "Fill out the following template and return only the completed text:\n"
        "Title: <short heading>\n"
        "Rationale: <brief reasoning referencing sentiment, risks and prior votes>\n"
        "Action: <specific on-chain steps>\n"
        "Expected Impact: <anticipated network effects>\n\n"
        f"{topics_section}"
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
    source_name: str,
    temperature: float | None = None,
    max_tokens: int | None = None,
    timeout: float | None = None,
    attempts: int = 1,
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
        else float(os.getenv("PROPOSAL_TIMEOUT", os.getenv("OLLAMA_TIMEOUT", "360")))
    )
    prompt = build_prompt(context_dict, source_name)
    last_error: ValueError | None = None
    for _ in range(max(1, attempts)):
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
        except ValueError as err:
            last_error = err
    # Fallback: always return a minimally structured draft so the CLI displays
    # a proposal even when parsing fails.
    return fallback_draft(context_dict, source_name)
