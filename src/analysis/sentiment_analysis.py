"""Compatibility wrapper for sentiment analysis functions."""
from __future__ import annotations

from typing import Iterable, Dict, Any

from agents.sentiment_analyser import (
    analyse_messages as _analyse_messages,
    _extract_json,
    simple_polarity,
)

__all__ = ["analyse_messages", "_extract_json", "simple_polarity"]


def analyse_messages(messages: Iterable[str]) -> Dict[str, Any]:
    """Delegate to :func:`agents.sentiment_analyser.analyse_messages`."""
    return _analyse_messages(messages)
