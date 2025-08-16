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
- **Predictive Outcome Modeling (planned):** Lightweight ML models to forecast proposal success and voter turnout (not yet implemented).
- **Chain-Agnostic Design:** Integrates with Polkadot’s OpenGov pallet; easily adaptable to other platforms.
- **Modular Pipeline:** Separate modules for data collection, analysis, LLM inference, and on-chain logging.
- **Audit Trail:** Every output is hashed and stored on-chain or in versioned files for transparency.

> **Current Status:** The context-generation agent, prediction-analysis agent, on-chain Governor integration, community-platform submission, and knowledge-base feedback loops are not yet implemented in this MVP.

### Roadmap

- Complete context-generation module for richer governance context.
- Develop prediction-analysis agent for outcome forecasting.
- Integrate with on-chain Governor for autonomous proposal submission.
- Establish RAG feedback loop to continuously update the knowledge base.

### Current Implementation Status

**Data Layer**

- Off-chain data scraping via BeautifulSoup — implemented
- On-chain data collection via web3.py — implemented
- Knowledge base auto-generates `data/input/PKD Governance Data.xlsx` on demand — implemented

**Agents Layer**

 - Data-collector, sentiment-analysis, proposal-generator, proposal-submission — implemented
 - Context-generator, prediction-analysis — not yet implemented

**Execution Layer**

- Governor smart contract — not yet implemented
- Community platform connectors — post proposal summaries to Discord, Telegram, and Twitter

**RAG Feedback Loops**

 - Context-generator → knowledge base — not yet implemented
 - Proposal-submission → knowledge base — not yet implemented
 - Governor executed results → knowledge base — not yet implemented

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
  ollama server
  ```
- Pull a model:
  ```bash
  ollama pull gemma3:4b
  # or
  ollama pull deepseek-r1:1.5b
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
```

`SUBSTRATE_NODE_URL` should point to a Substrate RPC endpoint. Common choices
include `wss://rpc.polkadot.io` for Polkadot mainnet or
`wss://westend-rpc.polkadot.io` for the Westend testnet. The
`SUBSTRATE_PRIVATE_KEY` is the signing key used by the execution agent when
submitting OpenGov transactions and must be funded for deposits. The Discord,
Telegram, and Twitter variables enable posting proposal summaries to those
platforms via the execution layer connectors.

`NEWS_LOOKBACK_DAYS` controls the number of past days of RSS items retrieved by
the news fetcher.

#### Data Weighting System

APOLLO merges sentiment, news, on‑chain metrics, and historical governance
signals into a single context for the LLM. Each `DATA_WEIGHT_*` environment
variable is a numeric multiplier that adjusts how strongly a given source
affects that context. Values greater than `1` amplify a source, while values
between `0` and `1` down‑weight it. `NEWS_LOOKBACK_DAYS` sets the recency window
for RSS items (default `3` days) so only fresh articles influence proposal
drafts. The example `.env` above shows one possible weighting split, but any
combination can be used to suit local priorities.

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

### 5. Run the Main Pipeline

```bash
python src/main.py
```
- Orchestrates the full workflow: sentiment analysis, data fetch, KPI analysis, LLM-based proposal generation, and output.

> **Tip:** The first run may take longer due to model downloads and embedding builds. Subsequent runs are faster.

### 6. Post Summaries to Community Platforms

```python
from src.execution.discord_bot import post_summary as discord_post
from src.execution.telegram_bot import post_summary as telegram_post
from src.execution.twitter_bot import post_summary as twitter_post

discord_post("Example proposal summary")
telegram_post("Example proposal summary")
twitter_post("Example proposal summary")
```
- Sends a text summary to Discord, Telegram, and Twitter using the configured credentials. For community sentiment, APOLLO also monitors Reddit's r/Polkadot via `src/data_processing/social_media_scraper.py`.

### 7. Review Prediction Accuracy

After `main.py` completes, APOLLO prints a prediction‑accuracy table comparing forecasted outcomes with actual referendum results. When no current evaluations are available, the system samples five historical executed referenda to populate this table.

> **Prerequisite:** `data/input/PKD Governance Data.xlsx` must exist and include executed referenda (e.g., populate it via `python src/data_processing/referenda_updater.py`). Without this data the fallback accuracy report cannot be generated.

### 8. Draft Ranking & Workbook Storage

For each data source (chat, forum, news, etc.) APOLLO drafts a proposal and
forecasts its likelihood of approval. These drafts are ranked by the
`approval_prob` produced by the forecasting step, and the highest‑scoring draft
is selected as the main proposal. Every generated draft is still persisted in
the governance workbook at `data/input/PKD Governance Data.xlsx` under the
`Proposals` sheet with a `stage` of `draft`. The final chosen text is recorded
again with `stage` set to `final`, and any on‑chain submission adds a
`submission_id` with `stage` set to `submitted` so that all iterations remain
auditable.

---

## 6. Directory Structure

```
apollo-governance/
├── .env
├── README.md
├── requirements.txt
├── LICENSE
├── data/
│   ├── input/
│   │   └── (generated) PKD Governance Data.xlsx
│   ├── output/
│   │   ├── referenda_failures.csv
│   │   ├── blocks_last1days.json
│   └── generated_proposals/
│       ├── proposal_YYYYMMDD_HHMMSS.txt
│       └── context_YYYYMMDD_HHMMSS.json
├── tests/
│   ├── test_sentiment_analysis.py
│   ├── test_governance_analysis.py
│   └── test_blockchain_metrics.py
├── src/
│   ├── main.py
│   ├── utils/
│   │   └── helpers.py
│   ├── llm/
│   │   └── ollama_api.py
│   ├── analysis/
│   │   ├── sentiment_analysis.py
│   │   ├── governance_analysis.py
│   │   └── blockchain_metrics.py
│   └── data_processing/
│       ├── referenda_updater.py
│       ├── blockchain_data_fetcher.py
│       ├── social_media_scraper.py
│       └── news_fetcher.py
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
