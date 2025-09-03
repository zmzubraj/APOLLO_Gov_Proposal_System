"""
ollama_api.py
-------------
Light‑weight wrapper around the local Ollama HTTP API
to run Deepseek R1‑1.5b (or any other installed model).

Ollama docs: https://github.com/ollama/ollama/blob/main/docs/api.md
"""

from __future__ import annotations
import os
import requests
from typing import Dict, Any, Optional

# -----------------------------------------------------------------------------
# Configuration
# -----------------------------------------------------------------------------
OLLAMA_HOST = os.getenv("OLLAMA_HOST", "http://localhost:11434")
GENERATE_URL = f"{OLLAMA_HOST.rstrip('/')}/api/generate"
EMBED_URL = f"{OLLAMA_HOST.rstrip('/')}/api/embeddings"

# Default model you’ve installed locally
# DEFAULT_MODEL = os.getenv("OLLAMA_MODEL", "deepseek-r1:1.5b")  # ← colon!

DEFAULT_MODEL = os.getenv("OLLAMA_MODEL", "gemma3:4b")

# Requests timeout (seconds)
DEFAULT_TIMEOUT = float(os.getenv("OLLAMA_TIMEOUT", "240"))


# -----------------------------------------------------------------------------
# Core helpers
# -----------------------------------------------------------------------------
class OllamaError(RuntimeError):
    """Raised when the Ollama server returns a non‑200 or malformed response."""


def _post(url: str, payload: Dict[str, Any], *, timeout: float = DEFAULT_TIMEOUT) -> Dict[str, Any]:
    """Internal helper with basic error handling.

    This wraps :func:`requests.post` so that network issues or non-2xx responses
    raise :class:`OllamaError` with a helpful message.  The previous
    implementation surfaced raw ``requests`` exceptions which bubbled up and
    crashed the application when the local Ollama server was not running.
    """

    try:
        resp = requests.post(url, json=payload, timeout=timeout)
        resp.raise_for_status()
        return resp.json()
    except Exception as exc:  # noqa: BLE001
        raise OllamaError(f"Ollama request failed: {exc}") from exc


# -----------------------------------------------------------------------------
# Public API
# -----------------------------------------------------------------------------
def generate_completion(
        prompt: str,
        model: str = DEFAULT_MODEL,
        system: Optional[str] = None,
        temperature: float = 0.2,
        max_tokens: int | None = None,
        timeout: float = DEFAULT_TIMEOUT,
) -> str:
    """
    Send a prompt to Ollama and return the generated text (non‑streaming).

    Parameters
    ----------
    prompt : str
        The user prompt (main content).
    model : str
        Model name inside Ollama (`ollama list` to see installed models).
    system : str | None
        Optional system prompt prepended to `prompt`.
    temperature : float
        Sampling temperature (0–1).
    max_tokens : int | None
        Optional limit on generated tokens.
    timeout : float
        Request timeout in seconds.

    Returns
    -------
    str
        The model’s full completion.
    """
    payload: Dict[str, Any] = {
        "model": model,
        "prompt": prompt if system is None else f"<|system|>\n{system}\n<|user|>\n{prompt}",
        "stream": False,
        "options": {
            "temperature": temperature,
        },
    }
    if max_tokens:
        payload["options"]["num_predict"] = max_tokens

    data = _post(GENERATE_URL, payload, timeout=timeout)
    return data.get("response", "").strip()


def embed_text(
        text: str,
        model: str = DEFAULT_MODEL,
        *,
        timeout: float = DEFAULT_TIMEOUT,
) -> list[float]:
    """Obtain an embedding vector for the given text.

    Parameters
    ----------
    text : str
        Text to embed.
    model : str
        Model name inside Ollama.
    timeout : float
        Request timeout in seconds.

    Returns
    -------
    list[float]
        Embedding vector.
    """
    data = _post(EMBED_URL, {"model": model, "prompt": text}, timeout=timeout)
    return data.get("embedding", [])


# -----------------------------------------------------------------------------
# Ollama Health check
# -----------------------------------------------------------------------------

def check_server():
    try:
        requests.get(f"{OLLAMA_HOST.rstrip('/')}/api/health", timeout=5)
    except Exception as err:
        raise OllamaError(f"Ollama server not running on {OLLAMA_HOST}: {err}")


# -----------------------------------------------------------------------------
# Quick standalone test
# -----------------------------------------------------------------------------
if __name__ == "__main__":
    test_prompt = "Briefly describe Polkadot OpenGov in one sentence."
    try:
        check_server()
        answer = generate_completion(test_prompt)
        print("✅ Ollama responded:\n", answer)
    except OllamaError as e:
        print("❌", e)
