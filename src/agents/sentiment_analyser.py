"""Sentiment analysis agent providing message summaries."""
from __future__ import annotations

import json
import re
import textwrap
from typing import Iterable, Dict, Any

from llm.ollama_api import generate_completion

POS = re.compile(r"\b(great|good|awesome|up|bull|positive|love)\b", re.I)
NEG = re.compile(r"\b(bad|terrible|down|bear|negative|hate|risk)\b", re.I)


def _extract_json(text: str) -> dict | None:
    """Pull the first JSON object found in the text."""
    match = re.search(r"\{.*\}", text, re.S)
    if not match:
        return None
    try:
        return json.loads(match.group(0))
    except json.JSONDecodeError:
        return None


def simple_polarity(text: str) -> float:
    """Very naive fallback sentiment score."""
    pos = len(POS.findall(text))
    neg = len(NEG.findall(text))
    total = pos + neg or 1
    return (pos - neg) / total


SYSTEM_PROMPT = textwrap.dedent(
    """
    You are a concise blockchain community-analysis assistant.
    Given raw Discord / Telegram / X messages, return JSON with:
      sentiment_score : float  # –1 (very negative) … 1 (very positive)
      summary         : str    # 2‑3 sentence plain‑English recap
      key_topics      : list[str]  # max 5 bullet keywords / phrases
    Only output valid minified JSON – no commentary, no markdown.
    """
).strip()


def analyse_messages(messages: Iterable[str]) -> Dict[str, Any]:
    """Run LLM sentiment analysis over ``messages``."""
    raw_text = "\n".join(messages).strip()[:8000]

    try:
        response = generate_completion(
            prompt=raw_text,
            system=SYSTEM_PROMPT,
            temperature=0.1,
            max_tokens=256,
            model="gemma3:4b",
        )
        result = _extract_json(response)
        if result is None:
            raise ValueError("No JSON returned")
        for k in ("sentiment_score", "summary", "key_topics"):
            result.setdefault(k, "")
        return result
    except Exception:
        score = simple_polarity(raw_text)
        return {
            "sentiment_score": score,
            "summary": "LLM fallback – basic polarity calculated.",
            "key_topics": [],
        }
