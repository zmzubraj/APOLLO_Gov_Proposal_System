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
- **Retrieval-Augmented Knowledge Base:** Embeds and indexes historical referenda and discussions for real-time retrieval-augmented generation (RAG).
- **Predictive Outcome Modeling:** Trains lightweight ML models (e.g., LightGBM) on past votes to predict proposal success and turnout.
- **Chain-Agnostic Design:** Integrates with Polkadot’s OpenGov pallet; easily adaptable to other platforms.
- **Modular Pipeline:** Separate modules for data collection, analysis, LLM inference, and on-chain logging.
- **Audit Trail:** Every output is hashed and stored on-chain or in versioned files for transparency.

#### 3.1 Core Capabilities

- **LLM-Driven Proposal Analysis**
  1. Streams new proposals to APOLLO’s off-chain worker.
  2. LLM “Analysis Agent” ingests proposal text and relevant context.
  3. Outputs concise summaries, risk tags, and classifications.

- **Predictive Forecasting**
  1. “Predictor Agent” combines structured and semantic features.
  2. Runs ML models to estimate:
      - **`P_pass`**: Probability of proposal passing.
      - **Turnout Estimate:** Forecasted voter participation.
      - **Sentiment Trend:** Directional bias from recent discussions.

- **Autonomous Proposal Generation**
  1. “Planning Agent” crafts proposals from high-level objectives.
  2. Uses RAG to reference similar past proposals.
  3. LLM generates draft text and transaction payloads.

- **On-Chain Orchestration & Auditability**
  1. All agent decisions are recorded on-chain via a specialized pallet.
  2. Stakeholders can query the registry to verify APOLLO’s reasoning.
  3. APOLLO can propose or vote automatically if configured.

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

#### 3. Install Python Dependencies

```bash
pip install --upgrade pip
pip install -r requirements.txt
```

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
```

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
│   │   └── PKD Governance Data.xlsx
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
