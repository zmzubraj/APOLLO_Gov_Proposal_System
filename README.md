# APOLLO  
**Autonomous Predictive On-Chain Legislative Learning Orchestrator**  
*A Generalized LLM-Driven Governance Framework for Blockchain Networks*  

---

## 1. Introduction

APOLLO is a comprehensive governance automation framework that leverages Large Language Models (LLMs) and predictive analytics to analyze, forecast, and generate on-chain proposals. While designed to be chain-agnostic, the Minimum Viable Product (MVP) is prototyped on Polkadot (Substrate), showcasing how an LLM-centric multi-agent pipeline can ingest both on-chain and off-chain data, reason over governance context, and propose data-driven legislative actions.

**Key Features:**
- **Semantic Analysis:** LLM-powered summarization and classification of proposals and community discussions.
- **Predictive Forecasting:** Machine learning models trained on historical referenda to estimate approval probabilities and voter turnout.
- **Autonomous Action:** Agents capable of drafting, submitting, or voting on proposals autonomously.
- **Auditability:** All agent outputs (summaries, predictions, drafts) are immutably logged on-chain or in a central knowledge base.

APOLLO empowers blockchain communities with faster, more transparent, and inclusive governance—without compromising decentralization or accountability.

---

## 2. Challenges in Blockchain Governance

1. **Information Overload**
    - Proposals are increasingly complex, requiring manual review of lengthy texts, leading to fatigue and shallow analysis.
2. **Low Participation & Whale Domination**
    - Confusing UIs and technical proposals deter participation; large stakeholders often dominate outcomes.
3. **Rigid, Rule-Based Workflows**
    - Governance relies on static scripts/templates, which struggle to adapt to evolving community norms. Off-chain discussions remain siloed from on-chain voting.
4. **Lack of Real-Time Insight**
    - Disconnected data sources prevent communities from identifying high-impact proposals, forecasting outcomes, or detecting trends in real time.

These issues result in slow proposal cycles, low turnout, and governance outcomes that may not reflect broad consensus. APOLLO addresses these gaps with real-time intelligence, predictive analytics, and natural language guidance throughout the governance lifecycle.

---

## 3. APOLLO Solution Overview

APOLLO’s modular architecture is deployable on any blockchain supporting on-chain governance (proposal creation, voting, storage). The MVP demonstrates integration with Polkadot (Substrate), but the design is portable to Ethereum, Cosmos, Avalanche, and more.

### 📦 Features

- **LLM-Based Analysis:** Uses open-source LLMs (e.g., Gemma3:4B, Deepseek R1:1.5B) via Ollama for summarization, classification, and proposal generation.
- **Retrieval-Augmented Knowledge Base:** Stores governance data in an Excel workbook (`data/input/PKD Governance Data.xlsx`, auto-generated if missing) for retrieval-augmented generation (RAG). See [docs/workbook_structure.md](docs/workbook_structure.md) for worksheet details.
- **Predictive Outcome Forecasting:** Trainable logistic model (see `src/analysis/train_forecaster.py`) estimates approval probability and voter turnout from historical referenda.
- **Community Broadcast & Submission:** Connectors push proposal summaries to Discord, Telegram, and Twitter with optional Substrate proposal submission.
- **Chain-Agnostic Design:** Integrates with Polkadot’s OpenGov pallet; easily adaptable to other platforms.
- **Modular Pipeline:** Separate modules for data collection, analysis, LLM inference, and on-chain logging.
- **Audit Trail & Workbook Logging:** Proposals, context, referenda, and execution results are stored in versioned files for transparency.

> **Current Status:** Data collection, sentiment analysis, context generation, outcome forecasting, proposal drafting, community broadcasting, and Substrate submission stubs are implemented. Advanced prediction models, autonomous execution, and richer knowledge-base feedback loops remain under development.

### Roadmap

- Enhance outcome forecaster with richer machine-learning models.
- Harden on-chain Governor interface for autonomous proposal execution.
- Expand RAG feedback loop to continuously enrich the knowledge base.
- Build additional community-platform integrations and a simple UI/dashboard.

### Current Implementation Status

**Data Layer**

- Off-chain data scraping via BeautifulSoup — implemented
- On-chain data collection via web3.py — implemented
- Knowledge base auto-generates `data/input/PKD Governance Data.xlsx` on demand — implemented

**Agents Layer**

- Data-collector, sentiment-analysis, proposal-generator, context-generator, outcome-forecaster, proposal-submission — implemented

**Execution Layer**

- Governor smart contract interface — basic submission and execution helpers implemented
- Community platform connectors — send proposal summaries to Discord, Telegram, and Twitter

**RAG Feedback Loops**

- Context-generator → knowledge base — implemented
- Proposal-submission → knowledge base — implemented
- Governor executed results → knowledge base — implemented

#### 3.1 Core Capabilities

- **LLM-Driven Proposal Analysis**
  1. Streams new proposals to APOLLO’s off-chain worker.
  2. LLM “Analysis Agent” ingests proposal text and relevant context.
  3. Outputs concise summaries, risk tags, and classifications.

- **Predictive Forecasting** *(planned)*
  1. “Predictor Agent” will combine structured and semantic features.
  2. Planned outputs include:
      - **`P_pass`**: Probability of proposal passing.
      - **Turnout Estimate:** Forecasted voter participation.
      - **Sentiment Trend:** Directional bias from recent discussions.

- **Autonomous Proposal Generation**
  1. “Planning Agent” crafts proposals from high-level objectives.
  2. Uses RAG to reference similar past proposals.
  3. LLM generates draft text and transaction payloads.

- **On-Chain Orchestration & Auditability** *(planned)*
  1. Agent decisions will be recorded on-chain via a specialized pallet.
  2. Stakeholders will be able to query the registry to verify APOLLO’s reasoning.
  3. APOLLO will propose or vote automatically if configured.

#### 3.2 Example: Polkadot Integration

- **Referenda Updater:** Polls for new referenda, collects data, logs failures.
- **Blockchain Data Fetcher:** Retrieves and aggregates recent block data.
- **Social & News Analysis:** Scrapes forums/news, applies LLM sentiment analysis.
- **LLM Interface:** Formats prompts and calls local LLMs for summaries/drafts.
- **Main Orchestrator:** Coordinates pipelines and outputs generated proposals.
---

## 4. Setup Guide

Follow these steps to configure and run the APOLLO MVP. Requires Python 3.9+, Substrate node access (optional), and basic CLI skills.

### 4.1 Prerequisites

- **OS:** Windows 10/11, macOS 12+, or modern Linux
- **Python:** 3.9 or 3.10, with `pip`
- **Ollama:** ≥ 0.1.0, with a supported LLM image (e.g., `gemma3:4b`)
- **Substrate Node:** For live on-chain data (optional)
- **Ethereum Node:** For interacting with EVM chains via Web3 (optional)
- **API Keys:** `SUBSCAN_API_KEY` for on-chain metrics; social/news API keys as needed

---

### 4.2 Installation

#### 1. Clone the Repository

```bash
git clone https://github.com/zmzubraj/APOLLO_Gov_Proposal_System.git
cd apollo-governance
```

#### 2. Create & Activate a Virtual Environment

```bash
python3 -m venv ./venv

# Windows
.\venv\Scripts\activate

# macOS/Linux
source ./venv/bin/activate
```

#### 3. Install Python Dependencies (includes Web3 for EVM chains)

```bash
pip install --upgrade pip
pip install -r requirements.txt
```

These commands install core libraries, including Web3 and Ethereum tooling.

*If `requirements.txt` is missing, install dependencies manually.*

#### 4. Install & Configure Ollama

- Download and install Ollama: https://ollama.com/download
- Start the Ollama server:
  ```bash
  ollama serve
  ```
- Manage models:
  ```bash
  ollama pull gemma3:4b      # download Gemma 3 4B
  ollama rm deepseek-r1:1.5b # optional: remove an unused model
  ollama list                # list available models
  ```
- Test the LLM API:
  ```bash
  ollama run gemma3:4b
  ```
- Update the model reference in `src/llm/ollama_api.py`:
  ```python
  MODEL_NAME = "gemma3:4b"  # or "deepseek-r1:1.5b"
  ```

#### 5. Environment Configuration

Create a `.env` file in the project root:

```env
 SUBSCAN_API_KEY=your_subscan_api_key_here
 Optional: NEWS_API_KEY=your_news_api_key
 REDDIT_CLIENT_ID=...
 REDDIT_CLIENT_SECRET=...
 SUBSTRATE_NODE_URL=wss://rpc.polkadot.io
 SUBSTRATE_PRIVATE_KEY=hex_encoded_sr25519_key
 # Community platform credentials
 DISCORD_WEBHOOK_URL=https://discord.com/api/webhooks/...
 TELEGRAM_BOT_TOKEN=your_telegram_bot_token
 TELEGRAM_CHAT_ID=your_chat_id
 TWITTER_BEARER=your_twitter_api_bearer_token
 # Relative weighting of data sources
 DATA_WEIGHT_CHAT=0.25         # real-time chat sentiment
 DATA_WEIGHT_FORUM=0.25        # long-form forum posts
 DATA_WEIGHT_NEWS=0.10         # news articles
 DATA_WEIGHT_CHAIN=0.20        # on-chain metrics
 DATA_WEIGHT_GOVERNANCE=0.20   # past governance data

 # Recency controls
 NEWS_LOOKBACK_DAYS=3          # days of news to fetch
# Fallback historical evaluation
# HISTORICAL_SAMPLE_SEED=1      # optional seed for sampling historical referenda
# Minimum confidence to label a draft as passing
MIN_PASS_CONFIDENCE=0.80

# Optional EVM block collection
ENABLE_EVM_FETCH=false         # set true to pull EVM blocks
EVM_RPC_URL=https://mainnet.infura.io/v3/your_project_id
EVM_START_BLOCK=0
EVM_END_BLOCK=latest
```

See [docs/environment_variables.md](docs/environment_variables.md) for a full description of every variable and its default role.

**Optional EVM chain support:** Set `ENABLE_EVM_FETCH=true` and provide an `EVM_RPC_URL` to pull blocks from an Ethereum-compatible chain. `EVM_START_BLOCK` and `EVM_END_BLOCK` bound the collection range.

**Per-source weighting controls:** The `DATA_WEIGHT_*` variables tune how chat, forum, news, on-chain, and governance data influence proposal ranking. Ensure the weights sum to `1.0`.

`SUBSTRATE_NODE_URL` should point to a Substrate RPC endpoint. Common choices
include `wss://rpc.polkadot.io` for Polkadot mainnet or
`wss://westend-rpc.polkadot.io` for the Westend testnet. The
`SUBSTRATE_PRIVATE_KEY` is the signing key used by the execution agent when
submitting OpenGov transactions and must be funded for deposits. The Discord,
Telegram, and Twitter variables enable posting proposal summaries to those
platforms via the execution layer connectors.

`NEWS_LOOKBACK_DAYS` controls the number of past days of RSS items retrieved by
the news fetcher. `HISTORICAL_SAMPLE_SEED` can be set to a **non-zero** integer
to make historical prediction sampling reproducible; omit it or set it to `0`
to allow nondeterministic selection. `MIN_PASS_CONFIDENCE` defines the approval
probability threshold used to label draft proposals as "Pass" in the forecast
summary table.

When `ENABLE_EVM_FETCH` is set to `true`, APOLLO also pulls blocks from any
EVM‑compatible chain specified by `EVM_RPC_URL`. `EVM_START_BLOCK` and
`EVM_END_BLOCK` define the range of blocks to fetch (use `latest` to stream to
the chain tip). Retrieved block data is added to pipeline outputs under the
`"evm_blocks"` key alongside other collected datasets.

#### Data Weighting System

APOLLO merges sentiment, news, on‑chain metrics, and historical governance
signals into a single context for the LLM. The `DATA_WEIGHT_*` environment
variables determine how much influence each source has in that merge—raise a
weight to emphasize a source or lower it to soften its impact. Values greater
than `1` amplify a source, while values between `0` and `1` down‑weight it. The
weights typically sum to `1`, but any combination can be used to suit local
priorities. `NEWS_LOOKBACK_DAYS` sets the recency window for RSS items (default
`3` days) so only fresh articles influence proposal drafts.

---

## 5. Usage

### 1. Collect Social & News Sentiment

```bash
python src/analysis/sentiment_analysis.py
```
- Scrapes configured social/news sources and outputs sentiment summaries.

### 2. Fetch On-Chain Governance Data

```bash
python src/data_processing/referenda_updater.py
```
- Updates the governance knowledge base with new referenda.

### 3. Fetch & Aggregate Blockchain Metrics

```bash
python src/data_processing/blockchain_data_fetcher.py
```
- Aggregates recent block data for analysis.

### 4. Generate Governance KPIs & Insights

```bash
python src/analysis/governance_analysis.py
```
- Computes historical KPIs and outputs summaries.

### 5. Train the Referendum Outcome Forecaster

Refresh the referendum forecasting model after you have collected and
aggregated governance data:

1. Ensure `data/input/PKD Governance Data.xlsx` contains executed
   referenda. Populate it via
   `python src/data_processing/referenda_updater.py` if necessary.
2. Run the training script:

   ```bash
   python src/analysis/train_forecaster.py
   ```

   The script fits a logistic regression model and writes the parameters
   to `models/referendum_model.json`.
3. Replace or commit the updated `models/referendum_model.json` to use the
   new model in subsequent forecasts.

### 6. Run the Main Pipeline

```bash
python src/main.py
```
- Orchestrates the full workflow: sentiment analysis, data fetch, KPI analysis, LLM-based proposal generation, and output.

> **Tip:** The first run may take longer due to model downloads and embedding builds. Subsequent runs are faster.

### 7. Post Summaries to Community Platforms

```python
from src.execution.discord_bot import post_summary as discord_post
from src.execution.telegram_bot import post_summary as telegram_post
from src.execution.twitter_bot import post_summary as twitter_post

discord_post("Example proposal summary")
telegram_post("Example proposal summary")
twitter_post("Example proposal summary")
```
- Sends a text summary to Discord, Telegram, and Twitter using the configured credentials. For community sentiment, APOLLO also monitors X/Twitter, the Polkadot Forum, CryptoRank, Binance Square, and Reddit's r/Polkadot via `src/data_processing/social_media_scraper.py`. Set `TWITTER_BEARER` to use the official X API; the other sources rely on public endpoints and require no additional credentials.

### 8. Review Prediction Accuracy

After `main.py` completes, APOLLO prints a prediction‑accuracy table comparing forecasted outcomes with actual referendum results. It also prints a draft forecast table listing each generated draft, its predicted outcome, confidence, runtime and margin of error. When no current evaluations are available, the system samples five historical executed referenda to populate this table.

> **Prerequisite:** `data/input/PKD Governance Data.xlsx` must exist and include executed referenda (e.g., populate it via `python src/data_processing/referenda_updater.py`). Without this data the fallback accuracy report cannot be generated.

### 9. Draft Generation & Ranking

APOLLO produces a proposal draft for **each data source** (chat, forum, news,
on‑chain metrics, and historical governance data). The influence of each source
is controlled by the `DATA_WEIGHT_*` environment variables:

```bash
DATA_WEIGHT_CHAT=0.25         # real-time chat sentiment
DATA_WEIGHT_FORUM=0.25        # long-form forum posts
DATA_WEIGHT_NEWS=0.10         # news articles
DATA_WEIGHT_CHAIN=0.20        # on-chain metrics
DATA_WEIGHT_GOVERNANCE=0.20   # past governance data
```

These weights typically sum to `1.0` and are applied when ranking drafts.

1. **Collect & Draft:** For each platform, the pipeline gathers data, builds a
   context, and generates a proposal draft with the LLM.
2. **Forecast:** An approval probability is predicted for every draft.
3. **Score & Rank:** A draft's `score` is computed as
   `approval_prob * DATA_WEIGHT_*`, and the highest‑scoring draft above
   `MIN_PASS_CONFIDENCE` becomes the main proposal.

Every generated draft is stored in the governance workbook at
`data/input/PKD Governance Data.xlsx` on the `Proposals` sheet with `stage`
`draft`. The selected draft is written again with `stage` `final`, and any
on‑chain submission adds a `submission_id` with `stage` `submitted` to maintain
an audit trail of all iterations.

In addition to the workbook, the pipeline now serialises each call to
`record_proposal` as JSON under `data/output/generated_proposals/`. Drafts are
saved as `draft_<source>_<ts>.json`, while the final chosen proposal is also
persisted as `proposal_<ts>.json`. These files capture the proposal text,
originating source, a context snippet, and its forecast for easy offline
inspection.

---

## 6. Directory Structure

```
apollo-governance/
├── .env
├── README.md
├── requirements.txt
├── data/
│   ├── input/
│   └── output/
├── docs/
├── models/
├── src/
│   ├── main.py
│   ├── agents/
│   │   ├── context_generator.py
│   │   ├── outcome_forecaster.py
│   │   └── …
│   ├── analysis/
│   │   ├── blockchain_metrics.py
│   │   ├── governance_analysis.py
│   │   ├── prediction_evaluator.py
│   │   ├── train_forecaster.py
│   │   └── …
│   ├── data_processing/
│   │   ├── proposal_store.py
│   │   ├── referenda_updater.py
│   │   └── …
│   ├── execution/
│   │   ├── discord_bot.py
│   │   ├── telegram_bot.py
│   │   ├── twitter_bot.py
│   │   └── governor_interface.py
│   ├── reporting/
│   │   └── summary_tables.py
│   ├── llm/
│   │   └── ollama_api.py
│   └── utils/
│       ├── helpers.py
│       └── validators.py
└── tests/
    ├── test_pipeline.py
    ├── test_prediction_analysis.py
    └── …  # 40+ pytest modules
```

---

## 7. Contributing

We welcome contributions! To get started:

1. **Fork** the repository and create a new branch.
2. **Develop** your feature or improvement.
3. **Write Tests** for new modules where applicable.
4. **Submit a Pull Request** with details and motivation.
5. **Review & Discussion:** We’ll review and merge as appropriate.
6. **Star & Share:** If APOLLO helps you, please star and share!

---

## 8. Development Roadmap

 - **Upcoming Components:**
   - Context-generation agent for building governance context
   - Prediction-Analysis agent for outcome forecasting
   - On-chain Governor integration for autonomous proposal submission
   - Community-platform submission workflow
   - RAG feedback loop for continuous learning
- **MVP:** Basic pipeline (data ingestion → LLM inference → on-chain log)
- **Planned Improvements:**
  - Multi-chain smart contract adapters (Ethereum, Cosmos)
  - Enhanced agent safety guardrails
  - Real-time UI/dashboard (Flask or React)
- **Future:**
  - Decentralized LLM agent hosting (IPFS, on-chain compute)
  - Zero-knowledge proof of proposal generation
  - Incentive mechanisms for agent contributors

---

## 9. License

This project is released under the **MIT License**. See [LICENSE](./LICENSE) for details.

---

## Contact & Acknowledgments

- **Maintainer:** [Zubaer Mahmood Zubraj](https://github.com/zmzubraj)
- **Email:** zmzubraj@gmail.com

**Acknowledgments:**
- Early contributors and community testers
- Ollama for open-source LLM hosting
- Subscan API team for data access

Thank you for your interest in APOLLO! We look forward to your feedback and contributions. 🚀
