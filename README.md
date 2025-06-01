# APOLLO  
**Autonomous Predictive On-Chain Legislative Learning Orchestrator**  
*A Generalized LLM-Driven Governance Framework for Blockchain Networks*  

---

## 1. Introduction  
APOLLO is an end-to-end governance automation framework that combines Large Language Models (LLMs) with predictive analytics to analyze, forecast, and even generate on-chain proposals. While fully chain-agnostic, APOLLO’s Minimum Viable Product (MVP) has been prototyped on Polkadot (Substrate) to demonstrate how an LLM-centric multi-agent pipeline can ingest on-chain and off-chain data, reason over governance context, and propose data-backed legislative actions.  

Key features include:  
- **Semantic Analysis**: LLM-based summarization and classification of new proposals and community discussions.  
- **Predictive Forecasting**: Machine-learning models trained on historical referenda to estimate approval probability and voter turnout.  
- **Autonomous Action**: Agents that can draft “next-generation” proposals and optionally submit or vote on-chain.  
- **Auditability**: All agent outputs (LLM summaries, prediction scores, draft text) are immutably logged on-chain or persisted in a central knowledge base.  

APOLLO is designed to help give blockchain communities faster, more transparent, and more inclusive governance—without sacrificing decentralization or accountability.

---

## 2. Existing Problem in Blockchain Governance  
1. **Information Overload**  
   - Proposals are increasingly complex (multi-phase funding requests, nuanced protocol upgrades).  
   - Human reviewers or community members must manually sift through lengthy texts, resulting in fatigue or shallow reviews.  

2. **Low Participation & “Whale Domination”**  
   - Many token holders abstain because governance UIs are confusing or proposals require deep technical understanding.  
   - Large stakeholders (“whales”) can dominate outcomes, as a small group often drives discussions and votes.

3. **Static, Rule-Based Workflows**  
   - On-chain governance often relies on fixed scripts or templates (e.g. “Treasury Spend X,” “Parameter Y Change → update storage”), which cannot easily adapt to evolving community norms.  
   - Off-chain discussion platforms (forums, Discord) capture sentiment but are disconnected from the voting process, creating silos of communication.

4. **Lack of Real-Time Insight**  
   - Historical voting data, community sentiment, and external news are not integrated into a single feedback loop.  
   - Communities lack an automated, continuously updated “lens” to identify high-impact proposals, forecast outcomes, or detect emerging trends.  

As a result, blockchains face slow proposal turnarounds, low voter turnout, and governance outcomes that sometimes do not reflect broader stakeholder consensus. APOLLO addresses these shortcomings by delivering real-time intelligence, predictive forecasts, and natural‐language guidance directly into the governance lifecycle.

---

## 3. Solution Provided by APOLLO  
APOLLO’s generalized architecture can be deployed on any blockchain platform that supports on-chain governance semantics (proposal creation, voting, on-chain storage). The MVP is implemented on Polkadot (Substrate) as a reference use case, but the same design can be ported to Ethereum (via a governance smart contract), Cosmos, Avalanche, or other frameworks.

## 📦 Features

- **LLM-Based Analysis**: Uses an open-source LLM (e.g. Gemma3:4B or Deepseek R1:1.5B) via Ollama for summarization, classification, and proposal generation.
- **Retrieval-Augmented Knowledge Base**: Historical referenda and community discussion are embedded and indexed for real-time “Retrieval-Augmented Generation” (RAG).
- **Predictive Outcome Modeling**: Trains a lightweight ML model (e.g. LightGBM) on past votes to predict proposal success and turnout.
- **Chain-Agnostic Design**: Example integration with Polkadot’s OpenGov pallet; easily portable to Ethereum, Cosmos, or any Substrate-style runtime.
- **Modular Pipeline**: Separate modules for data collection (social news, on-chain metrics), analysis (sentiment, governance), LLM inference, and on-chain logging.
- **Audit Trail**: Every generated summary, predicted score, and proposed transaction is hashed and stored on-chain or in versioned files for transparency.


### 3.1 Core Capabilities  
- **LLM-Driven Proposal Analysis**  
  1. New proposals (on-chain events) are streamed to APOLLO’s off-chain worker.  
  2. An LLM “Analysis Agent” ingests the raw proposal text plus any relevant on-chain or off-chain context (forum posts, historical referenda).  
  3. The agent outputs a concise summary, risk tags (e.g. “high budget,” “security impact”), and classification (e.g. “Treasury Spend,” “Protocol Parameter Change”).

- **Predictive Forecasting**  
  1. A “Predictor Agent” combines structured features (deposit size, track/origin, vote history) and semantic features (LLM-extracted risk tags, sentiment scores).  
  2. It runs a machine-learning model (e.g. LightGBM) trained on historical governance data to produce:  
     - **`P_pass`**: Probability the proposal will pass.  
     - **Turnout Estimate**: Forecast of voter participation percentage.  
     - **Sentiment Trend**: Directional bias (positive/negative) gleaned from recent discussion.

- **Autonomous Proposal Generation**  
  1. A “Planning Agent” can craft new proposals when given high-level objectives (e.g. “reduce inflation by 2%” or “increase validator incentives”).  
  2. It uses retrieval-augmented generation (RAG) to pull similar past proposals from the knowledge base.  
  3. The LLM then produces a draft text and a valid transaction‐payload (JSON) ready for on-chain submission.

- **On-Chain Orchestration & Auditability**  
  1. All agent decisions (LLM summaries, prediction scores, drafted proposals) are recorded on-chain via a specialized Substrate pallet (`pallet_apollo`).  
  2. Stakeholders can query the on-chain registry to verify how APOLLO arrived at its conclusions.  
  3. If configured, APOLLO’s multisig or governance account can automatically propose or vote according to community policies.

### 3.2 Example Polkadot Use Case  
Although APOLLO is chain-agnostic, the provided codebase demonstrates an integration with Polkadot’s OpenGov module:  
1. **Referenda Updater** (`data_processing/referenda_updater.py`):  
   - Continuously polls Polkadot’s democracy pallet to fetch new referenda IDs.  
   - Uses Subsquare/Squid to collect titles, content, timelines, and on-chain voting results.  
   - Fills missing data and logs failures to `data/output/referenda_failures.csv`.

2. **Blockchain Data Fetcher** (`data_processing/blockchain_data_fetcher.py`):  
   - Retrieves three days of historical block data (transactions, fees, timestamps).  
   - Aggregates per-day metrics for use in predictor features.

3. **Social & News Analysis** (`analysis/sentiment_analysis.py`, `analysis/news_analysis.py`):  
   - Scrapes community forums (e.g. Reddit r/Polkadot) and news RSS feeds.  
   - Applies a fallback LLM to extract sentiment scores, topic keywords, and risk flags.

4. **LLM Interface** (`llm/ollama_api.py`):  
   - Formats a structured prompt containing proposal metadata, sentiment analysis, historical KPI trends.  
   - Calls a local Ollama‐hosted LLM (e.g. `gemma3:4b`) to produce an actionable summary or draft.

5. **Main Orchestrator** (`main.py`):  
   - Coordinates the data pipelines, LLM calls, and final governance “proposal” generation.  
   - Writes generated proposals to `data/output/generated_proposals/` for review/submission.

By layering these modules, APOLLO transforms Polkadot’s raw governance events into an automated, LLM‐driven governance assistant.

---

## 4. How to Set Up APOLLO (Step-by-Step)

Below are the instructions to configure and run the APOLLO MVP on your local machine or server. These steps assume familiarity with Python 3.9+, Node/Substrate, and basic command-line usage.

### 4.1 Prerequisites

## 📋 Prerequisites

1. **Operating System**  
   - Windows 10/11, macOS 12+, or any modern Linux distro

2. **Python & Virtual Environment**  
   - Python 3.9 or 3.10  
   - `pip` for package installation  

3. **Ollama** (Local LLM server)  
   - Version ≥ 0.1.0 (must be installed and running)  
   - A supported LLM image (e.g. `gemma3:4b` or `deepseek-r1:1.5b`)  

4. **Substrate Node (Optional)**  
   - If you want to fetch live on-chain data via RPC, you need access to a Substrate-based node (e.g. Polkadot or your own local testnet).

5. **API Keys & Environment Variables**  
   - **`SUBSCAN_API_KEY`** – for Subscan REST API calls to fetch on-chain metrics.  
   - **Social/News API keys** (if scraping via official endpoints; optional).  

---

## 🛠 Installation & Setup

### 1. Clone the Repository  
```bash
git clone https://github.com/zmzubraj/APOLLO_Gov_Proposal_System.git
cd apollo-governance
```

### **2. Create & Activate a Python Virtual Environment**
```bash
python3 -m venv ./venv

# Windows
.\venv\Scripts\activate

# macOS/Linux
source ./venv/bin/activate
```


### 3. **Install Python Dependencies**
```bash
pip install --upgrade pip
pip install -r requirements.txt

```

>⚠️ If requirements.txt is missing, install manually:

### **4. Install & Configure Ollama**

1.  **Download & install Ollama\
    > **

    -   Follow instructions at
        > [[ollama.dev]{.underline}](https://ollama.dev/installation)
        > for your OS.

    -   Ensure the ollama binary is in your PATH.

2. **Verify Ollama Server
```bash
** ollama server

```

2.  This should start a background service listening on
    > http://127.0.0.1:11434 (default port).

3.  **Pull a Model
    > **

For example, to use Gemma3:4B:
```bash

ollama pull gemma3:4b

Or to use Deepseek r1:1.5B:\

ollama pull deepseek-r1:1.5b

```
-   

4. **Test the LLM API
** In a new terminal:
```bash
ollama run gemma3:4b
```
# You should see a prompt like:

# \>\>\> Send a message (/? for help)

5.  **Update Model Reference in src/llm/ollama_api.py
** Inside the file, ensure the model name matches your pulled model:
\
MODEL_NAME = \"gemma3:4b\" \# or \"deepseek-r1:1.5b\"

6.  If you want to switch models, simply change this constant.
