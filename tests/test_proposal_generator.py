from unittest.mock import patch

import pytest

from src.agents import proposal_generator


def test_build_prompt_omits_trending_topics_by_default(monkeypatch):
    monkeypatch.delenv("PROPOSAL_INCLUDE_TOPICS", raising=False)
    context = {"trending_topics": ["x"], "foo": "bar"}
    prompt = proposal_generator.build_prompt(context, "consolidated")
    assert "Trending Topics:" not in prompt


def test_build_prompt_includes_trending_topics_when_enabled(monkeypatch):
    monkeypatch.setenv("PROPOSAL_INCLUDE_TOPICS", "1")
    context = {"trending_topics": ["a", "b"], "foo": "bar"}
    prompt = proposal_generator.build_prompt(context, "consolidated")
    assert "Trending Topics:" in prompt


def test_draft_uses_build_prompt_and_ollama():
    context = {"foo": "bar"}
    expected_prompt = proposal_generator.build_prompt(context, "consolidated")
    sample = (
        "Title: T\n"
        "Rationale: R\n"
        "Action: A\n"
        "Expected Impact: E"
    )

    with patch(
        "src.agents.proposal_generator.ollama_api.generate_completion",
        return_value=sample,
    ) as mock_gen:
        result = proposal_generator.draft(context, "consolidated")

    mock_gen.assert_called_once_with(
        prompt=expected_prompt,
        system="You are Polkadot-Gov-Agent v1.",
        model="gemma3:4b",
        temperature=0.3,
        max_tokens=4096,
        timeout=360.0,
    )
    assert result == sample


def test_draft_strips_preamble_and_validates_sections():
    context = {}
    raw = (
        "Here is your proposal:\n"
        "Title: Improve Something\n"
        "Rationale: Because we should\n"
        "Action: Do the thing\n"
        "Expected Impact: Better network\n"
    )

    with patch(
        "src.agents.proposal_generator.ollama_api.generate_completion",
        return_value=raw,
    ):
        result = proposal_generator.draft(context, "consolidated")

    assert result.splitlines()[0].startswith("Title:")
    for heading in ["Title:", "Rationale:", "Action:", "Expected Impact:"]:
        assert heading in result
    assert "Here is your proposal" not in result


def test_draft_returns_raw_when_missing_sections():
    context = {}
    raw = "No structured output provided"

    with patch(
        "src.agents.proposal_generator.ollama_api.generate_completion",
        return_value=raw,
    ):
        result = proposal_generator.draft(context, "consolidated")

    # When headings are missing, the raw text should be returned unchanged
    assert result == raw


@pytest.mark.parametrize("source_name", ["consolidated", "news_feed", "social"])
def test_build_prompt_includes_sections_and_source_prefix(source_name):
    context = {}
    prompt = proposal_generator.build_prompt(context, source_name)
    # The second sentence should begin with the source name reference
    after_intro = prompt.split("You are an autonomous Polkadot governance agent. ")[1]
    assert after_intro.startswith(f"Using context derived from {source_name}")
    for section in ["Title:", "Rationale:", "Action:", "Expected Impact:"]:
        assert section in prompt


@pytest.mark.parametrize("missing", ["Title:", "Rationale:", "Action:", "Expected Impact:"])
def test_postprocess_draft_missing_section_raises(missing):
    lines = [
        "Title: T",
        "Rationale: R",
        "Action: A",
        "Expected Impact: E",
    ]
    text = "\n".join(line for line in lines if not line.startswith(missing))
    with pytest.raises(ValueError):
        proposal_generator.postprocess_draft(text)
