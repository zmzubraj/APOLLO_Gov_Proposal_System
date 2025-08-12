from unittest.mock import patch

from src.agents import proposal_generator


def test_draft_uses_build_prompt_and_ollama():
    context = {"foo": "bar"}
    expected_prompt = proposal_generator.build_prompt(context)

    with patch(
        "src.agents.proposal_generator.ollama_api.generate_completion",
        return_value="result",
    ) as mock_gen:
        result = proposal_generator.draft(context)

    mock_gen.assert_called_once_with(
        prompt=expected_prompt,
        system="You are Polkadot-Gov-Agent v1.",
        model="gemma3:4b",
        temperature=0.3,
        max_tokens=4096,
    )
    assert result == "result"
