"""
helpers.py
----------
Small shared utilities used across the Polkadot governance project.
"""

from __future__ import annotations
import json, re, datetime as dt
from typing import Any, Dict, Optional

# ────────────────────────────────────────────────────────────────────────────
# 1. Robust JSON extractor
# ────────────────────────────────────────────────────────────────────────────
_JSON_RE = re.compile(r"\{.*\}", re.S)


def extract_json_safe(text: str) -> Optional[Dict[str, Any]]:
    """
    Attempt to locate and parse the first JSON object in `text`.

    Handles common LLM quirks:
      • Fenced blocks ```json … ```
      • Extra commentary before/after
      • Trailing commas

    Returns
    -------
    dict | None
        Parsed JSON if successful, otherwise None.
    """
    # Strip code-fences
    cleaned = re.sub(r"```[\s\S]*?```", lambda m: m.group(0).strip("`"), text)
    match = _JSON_RE.search(cleaned)
    if not match:
        return None

    candidate = match.group(0)
    # Remove trailing commas that break JSON
    candidate = re.sub(r",\s*([}\]])", r"\1", candidate)

    try:
        return json.loads(candidate)
    except json.JSONDecodeError:
        return None


# ────────────────────────────────────────────────────────────────────────────
# 2. Date helpers
# ────────────────────────────────────────────────────────────────────────────
def utc_now_iso() -> str:
    """UTC timestamp like 2025-05-17T13:55:02Z."""
    return dt.datetime.now(dt.UTC).strftime("%Y-%m-%dT%H:%M:%SZ")


def days_ago_iso(days: int) -> str:
    """ISO date N days ago (UTC)."""
    return (dt.datetime.now(dt.UTC) - dt.timedelta(days=days)).strftime("%Y-%m-%d")


# ────────────────────────────────────────────────────────────────────────────
# 3. Simple pretty-print number (1,234.5 K DOT)
# ────────────────────────────────────────────────────────────────────────────
def abbrev_number(value: float, suffix: str = "") -> str:
    magnitude = 0
    while abs(value) >= 1000 and magnitude < 3:
        magnitude += 1
        value /= 1000.0
    return f"{value:.1f}{' KMB'[magnitude]}{suffix}"


# ────────────────────────────────────────────────────────────────────────────
# Stand-alone smoke test
# ────────────────────────────────────────────────────────────────────────────
if __name__ == "__main__":
    demo = """
    Here is your JSON:
    ```json
    {
      "digest": ["item1", "item2"],
      "risks": "testing"
    }
    ```
    thanks!
    """
    print("Extracted:", extract_json_safe(demo))
    print("Now:", utc_now_iso())
    print("Abbrev:", abbrev_number(1234567, " DOT"))
