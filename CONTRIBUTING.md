# Contributing to APOLLO

Thanks for contributing to APOLLO.

This repository mixes governance analysis, data collection, LLM prompting, and optional on-chain or community-platform integrations. The safest contributions are usually focused changes with clear tests or documentation updates.

## Local setup

Clone the repository and create a virtual environment from the project root.

```bash
git clone https://github.com/zmzubraj/APOLLO_Gov_Proposal_System.git
cd APOLLO_Gov_Proposal_System
python -m venv .venv
```

Activate the environment:

```bash
# Windows
.venv\Scripts\activate

# macOS/Linux
source .venv/bin/activate
```

Install runtime dependencies and pytest:

```bash
python -m pip install --upgrade pip
python -m pip install -r requirements.txt pytest
```

## Environment configuration

The application loads environment variables from a root `.env` file.

- For most documentation-only changes and many unit tests, live credentials are not required.
- For pipeline runs and live integrations, create a `.env` file at the repository root and supply the variables you need.
- Full variable descriptions live in [docs/environment_variables.md](docs/environment_variables.md).

Examples of integrations that may require real credentials or external services:

- Subscan and Substrate RPC access
- Ollama model serving
- Discord, Telegram, or X/Twitter broadcasting
- Optional EVM RPC access

## Running tests

Run the full test suite:

```bash
python -m pytest -q
```

Run a targeted test while working on a small change:

```bash
python -m pytest tests/test_workbook_creation.py -q
```

## Minimal offline smoke check

If you want a fast verification step that does not require live chain credentials, run:

```bash
python -m pytest tests/test_workbook_creation.py -q
```

This is a small offline check that validates workbook creation and basic local test wiring.

## Contribution scope

Good contributions for this repo include:

- Documentation improvements
- Small, well-tested pipeline fixes
- Additional unit tests for existing modules
- Developer-experience improvements such as setup or tooling docs

Please keep changes focused. If a change touches multiple areas, explain the rationale clearly in the pull request.

## Pull requests

Before opening a pull request:

1. Keep the branch focused on one task.
2. Run the most relevant tests for the files you touched.
3. Update docs when behavior or setup changes.
4. Call out any credential, network, or external-service assumptions in the PR description.

If your change cannot be tested fully offline, say what you validated locally and what still depends on external services.
