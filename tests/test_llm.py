import pytest

from llm import ollama_api


def test_post_raises_ollama_error(monkeypatch):
    def fake_post(url, json=None, timeout=None):
        raise RuntimeError("network down")

    monkeypatch.setattr(ollama_api.requests, "post", fake_post)
    with pytest.raises(ollama_api.OllamaError):
        ollama_api._post("http://test", {})


def test_generate_completion_builds_payload(monkeypatch):
    captured = {}

    def fake_post(url, payload):
        captured["url"] = url
        captured["payload"] = payload
        return {"response": "answer  "}

    monkeypatch.setattr(ollama_api, "_post", fake_post)

    res = ollama_api.generate_completion(
        "Q", model="m", system="sys", temperature=0.5, max_tokens=10
    )
    assert res == "answer"
    assert captured["url"] == ollama_api.GENERATE_URL
    payload = captured["payload"]
    assert payload["model"] == "m"
    assert payload["options"]["temperature"] == 0.5
    assert payload["options"]["num_predict"] == 10
    assert payload["stream"] is False
    assert payload["prompt"].startswith("<|system|>")
    assert "Q" in payload["prompt"]


def test_embed_text_uses_post(monkeypatch):
    def fake_post(url, payload):
        assert url == ollama_api.EMBED_URL
        assert payload == {"model": "m", "prompt": "text"}
        return {"embedding": [0.1, 0.2]}

    monkeypatch.setattr(ollama_api, "_post", fake_post)
    emb = ollama_api.embed_text("text", model="m")
    assert emb == [0.1, 0.2]
