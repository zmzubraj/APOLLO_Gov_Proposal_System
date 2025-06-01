"""
sentiment_analysis.py
---------------------
Summarise community chatter and return
• overall polarity score  (-1 … 1)
• brief natural‑language summary
• key topics or concerns
"""

from __future__ import annotations
import json
from typing import Iterable, Dict, Any
import textwrap
from src.llm.ollama_api import generate_completion

# ────────────────────────────────────────────────────────────────────────────
# Basic rule‑based polarity helper (backup if LLM unavailable)
# ────────────────────────────────────────────────────────────────────────────
import re

POS = re.compile(r"\b(great|good|awesome|up|bull|positive|love)\b", re.I)
NEG = re.compile(r"\b(bad|terrible|down|bear|negative|hate|risk)\b", re.I)


def _extract_json(text: str) -> dict | None:
    """
    Pull the first JSON object found in the text.
    Handles models that wrap with ```json ... ``` or extra prose.
    """
    match = re.search(r'\{.*\}', text, re.S)
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


# ────────────────────────────────────────────────────────────────────────────
# Main high‑level function
# ────────────────────────────────────────────────────────────────────────────
SYSTEM_PROMPT = textwrap.dedent(
    """
    You are a concise blockchain community‑analysis assistant.
    Given raw Discord / Telegram / X messages, return JSON with:
      sentiment_score : float  # –1 (very negative) … 1 (very positive)
      summary         : str    # 2‑3 sentence plain‑English recap
      key_topics      : list[str]  # max 5 bullet keywords / phrases
    Only output valid minified JSON – no commentary, no markdown.
    """
).strip()


def analyse_messages(messages: Iterable[str]) -> Dict[str, Any]:
    """
    Run Deepseek on concatenated messages to get structured sentiment.

    Parameters
    ----------
    messages : Iterable[str]
        Raw text snippets (one per message).

    Returns
    -------
    dict
        { "sentiment_score": float, "summary": str, "key_topics": [...] }
    """
    raw_text = "\n".join(messages).strip()[:8000]  # avoid exceeding context

    try:
        response = generate_completion(
            prompt=raw_text,
            system=SYSTEM_PROMPT,
            temperature=0.1,
            max_tokens=256,
            model="gemma3:4b",
        )
        # print("RAW:", response[:500], "...\n")
        result = _extract_json(response)
        if result is None:
            raise ValueError("No JSON returned")

        # sanity‑check required keys
        for k in ("sentiment_score", "summary", "key_topics"):
            result.setdefault(k, "")
        return result
    except Exception:
        # fallback tiny rule‑based score
        score = simple_polarity(raw_text)
        return {
            "sentiment_score": score,
            "summary": "LLM fallback – basic polarity calculated.",
            "key_topics": [],
        }


# ────────────────────────────────────────────────────────────────────────────
# Stand‑alone test
# ────────────────────────────────────────────────────────────────────────────
if __name__ == "__main__":
    dummy_msgs = [
        "Polkadot is pumping hard today 🔥🔥",
        "The new OpenGov referendum looks risky to me.",
        "Love the dev updates from parity!",
    ]
    print(analyse_messages(dummy_msgs))
