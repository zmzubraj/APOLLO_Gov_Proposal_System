"""
main.py
-------
Orchestrator: run the full data pipeline and create a governance proposal
ready to post on Polkadot OpenGov.

Run:
$ python src/main.py
"""

from __future__ import annotations
import json, pathlib, datetime as dt, os, time
from typing import Any
import pandas as pd
from dotenv import load_dotenv
from agents.data_collector import DataCollector
from data_processing.social_media_scraper import (
    collect_recent_messages,
    flatten_forum_topic,
)
from reporting.summary_tables import (
    print_data_sources_table,
    print_sentiment_embedding_table,
    print_draft_forecast_table,
    print_prediction_accuracy_table,
    print_timing_benchmarks_table,
    evaluate_historical_predictions,
    draft_onchain_proposal,
    summarise_draft_predictions,
)
from agents.sentiment_analyser import analyse_messages
from data_processing.news_fetcher import fetch_and_summarise_news
from data_processing.referenda_updater import update_referenda
# from data_processing.blockchain_data_fetcher import fetch_recent_blocks
from data_processing.blockchain_cache import get_recent_blocks_cached
from analysis.blockchain_metrics import summarise_blocks, summarise_evm_blocks
from analysis.governance_analysis import get_governance_insights
from agents.outcome_forecaster import forecast_outcomes
from analysis.prediction_evaluator import compare_predictions
from agents import proposal_generator
from agents.context_generator import build_context
from llm import ollama_api
from execution.broadcast import broadcast_proposal
from execution.governor_interface import (
    await_execution,
    execute_proposal,
    submit_preimage,
    submit_proposal,
)
from data_processing import proposal_store
from data_processing.proposal_store import record_proposal, record_execution_result


# --- main.py  (top of file) -----------------------------------------------
PROJECT_ROOT = pathlib.Path(__file__).resolve().parents[1]  # src/..
OUT_DIR = PROJECT_ROOT / "data" / "output" / "generated_proposals"
OUT_DIR.mkdir(parents=True, exist_ok=True)
load_dotenv()
MIN_PASS_CONFIDENCE = float(os.getenv("MIN_PASS_CONFIDENCE", "0.50"))
SENTIMENT_TEMPERATURE = float(os.getenv("SENTIMENT_TEMPERATURE", "0.2"))
SENTIMENT_MAX_TOKENS = int(os.getenv("SENTIMENT_MAX_TOKENS", "2048"))
PROPOSAL_TEMPERATURE = float(os.getenv("PROPOSAL_TEMPERATURE", "0.3"))
PROPOSAL_MAX_TOKENS = int(os.getenv("PROPOSAL_MAX_TOKENS", "4096"))
NEWS_TEMPERATURE = float(os.getenv("NEWS_TEMPERATURE", "0.2"))
NEWS_MAX_TOKENS = int(os.getenv("NEWS_MAX_TOKENS", "1024"))


def _refresh_workbook() -> None:
    """Re-ingest the governance workbook before running the pipeline."""
    try:
        proposal_store.ensure_workbook()
        proposal_store.load_proposals()
        proposal_store.load_execution_results()
        proposal_store.load_contexts()
    except Exception:
        # Workbook ingestion failures should not block pipeline execution
        pass

def main() -> None:
    start = dt.datetime.now(dt.UTC)
    stats: dict[str, Any] = {}
    phase_times: dict[str, float] = {}
    try:
        ollama_api.check_server()
        llm_available = True
    except ollama_api.OllamaError as err:  # pragma: no cover - network dependent
        print(f"⚠️ {err}")
        llm_available = False

    def _analyse(msgs: list[str]):
        if not llm_available:
            return {}
        try:
            try:
                return analyse_messages(
                    msgs,
                    temperature=SENTIMENT_TEMPERATURE,
                    max_tokens=SENTIMENT_MAX_TOKENS,
                )
            except TypeError:
                return analyse_messages(msgs)
        except ollama_api.OllamaError as exc:  # pragma: no cover - network dependent
            print(f"⚠️ Sentiment analysis failed: {exc}")
            return {}

    def _draft(ctx: dict[str, Any]):
        if not llm_available:
            return ""
        try:
            try:
                return proposal_generator.draft(
                    ctx,
                    temperature=PROPOSAL_TEMPERATURE,
                    max_tokens=PROPOSAL_MAX_TOKENS,
                )
            except TypeError:
                return proposal_generator.draft(ctx)
        except ollama_api.OllamaError as exc:  # pragma: no cover - network dependent
            print(f"⚠️ Proposal drafting failed: {exc}")
            return ""

    # ------------------------------ Ingestion ------------------------------
    t0 = time.perf_counter()
    def _news_fn():
        try:
            return fetch_and_summarise_news(
                temperature=NEWS_TEMPERATURE, max_tokens=NEWS_MAX_TOKENS
            )
        except TypeError:
            # Backwards compatibility for mocks without new parameters
            return fetch_and_summarise_news()

    data = DataCollector.collect(
        collect_recent_messages,
        _news_fn,
        get_recent_blocks_cached,
        stats=stats,
    )
    phase_times["ingestion_s"] = time.perf_counter() - t0

    msgs_by_source = data["messages"]
    trending_topics = data.get("trending_topics", [])
    stats.setdefault("sentiment_batches", [])

    # ----------------------- Analysis + Prediction ------------------------
    t1 = time.perf_counter()
    batch_id = 1
    all_msgs: list[str] = []
    sentiments_by_source: dict[str, Any] = {}
    for source, msgs in msgs_by_source.items():
        if msgs and isinstance(msgs[0], dict):
            flat = [flatten_forum_topic(m) for m in msgs]
        else:
            flat = msgs
        all_msgs.extend(flat)
        res = _analyse(flat)
        sentiments_by_source[source] = res
        raw_text = "\n".join(flat).strip()
        ctx_size = res.get(
            "message_size_kb",
            len(raw_text.encode("utf-8")) / 1024 if raw_text else 0.0,
        )
        if llm_available:
            try:
                ollama_api.embed_text(raw_text)
                embedded = True
            except Exception:
                embedded = False
        else:
            embedded = False
        stats["sentiment_batches"].append(
            {
                "batch_id": batch_id,
                "source": source,
                "ctx_size_kb": ctx_size,
                "sentiment": res.get("sentiment", ""),
                "confidence": res.get("confidence", 0.0),
                "embedded": embedded,
            }
        )
        batch_id += 1

    # Flatten all message lists for overall sentiment analysis
    sentiment = _analyse(all_msgs) if all_msgs else {}
    # sentiment = []

    news = data["news"]

    blocks = data["blocks"]
    chain_kpis = summarise_blocks(blocks)
    evm_blocks = data.get("evm_blocks", [])
    evm_kpis = summarise_evm_blocks(evm_blocks)
    # Perform sentiment analysis + embedding on-chain KPIs
    chain_text = json.dumps(chain_kpis)
    chain_res = _analyse([chain_text])
    chain_ctx_size = (
        len(chain_text.encode("utf-8")) / 1024 if chain_text else 0.0
    )
    if llm_available:
        try:
            ollama_api.embed_text(chain_text)
            chain_embedded = True
        except Exception:
            chain_embedded = False
    else:
        chain_embedded = False
    stats["sentiment_batches"].append(
        {
            "batch_id": batch_id,
            "source": "onchain",
            "ctx_size_kb": chain_ctx_size,
            "sentiment": chain_res.get("sentiment", ""),
            "confidence": chain_res.get("confidence", 0.0),
            "embedded": chain_embedded,
        }
    )
    batch_id += 1

    # chain_kpis = []

    print("🔄 Analysing governance history …")
    update_referenda(max_new=1500)  # refresh knowledge-base quickly
    gov_kpis = get_governance_insights(as_narrative=True)

    # Bundle context via agent including semantic KB retrieval
    keywords = gov_kpis.get("top_keywords", []) if isinstance(gov_kpis, dict) else []
    query = " ".join(keywords[:3])

    # ------------------------------------------------------------------
    # Draft a proposal per source using only that source's data combined
    # with chain/governance metrics.  These drafts are stored for later
    # ranking and analysis.
    # ------------------------------------------------------------------
    proposal_drafts: list[dict[str, str]] = []
    for source, msgs in msgs_by_source.items():
        if source == "news":
            continue
        ctx = build_context(
            sentiments_by_source.get(source, {}),
            {},
            chain_kpis,
            gov_kpis,
            evm_kpis,
            kb_query=query,
            trending_topics=trending_topics,
            summarise_snippets=True,
        )
        draft_text = _draft(ctx)
        t_pred = time.perf_counter()
        forecast = forecast_outcomes(ctx)
        prediction_time = time.perf_counter() - t_pred
        ctx["forecast"] = forecast
        proposal_drafts.append(
            {
                "source": source,
                "text": draft_text,
                "context": ctx,
                "forecast": forecast,
                "prediction_time": prediction_time,
            }
        )
        record_proposal(draft_text, None, stage="draft")

    if news:
        ctx_news = build_context(
            {},
            news,
            chain_kpis,
            gov_kpis,
            evm_kpis,
            kb_query=query,
            trending_topics=trending_topics,
            summarise_snippets=True,
        )
        news_draft = _draft(ctx_news)
        t_pred = time.perf_counter()
        news_forecast = forecast_outcomes(ctx_news)
        prediction_time = time.perf_counter() - t_pred
        ctx_news["forecast"] = news_forecast
        proposal_drafts.append(
            {
                "source": "news",
                "text": news_draft,
                "context": ctx_news,
                "forecast": news_forecast,
                "prediction_time": prediction_time,
            }
        )
        record_proposal(news_draft, None, stage="draft")

    chain_draft_info = draft_onchain_proposal(
        chain_res, chain_kpis, gov_kpis, evm_kpis, query, trending_topics
    )
    if chain_draft_info:
        proposal_drafts.append(chain_draft_info)

    stats["drafts"] = proposal_drafts
    stats["draft_predictions"] = summarise_draft_predictions(
        proposal_drafts, MIN_PASS_CONFIDENCE
    )

    # Select best draft (fallback to consolidated context if none)
    if proposal_drafts:
        best_draft = max(
            proposal_drafts,
            key=lambda d: d.get("forecast", {}).get("approval_prob", 0.0),
        )
        context = best_draft["context"]
        forecast = best_draft["forecast"]
        proposal_text = best_draft["text"]
    else:
        context = build_context(
            sentiment,
            news,
            chain_kpis,
            gov_kpis,
            evm_kpis,
            kb_query=query,
            trending_topics=trending_topics,
            summarise_snippets=True,
        )
        t_pred = time.perf_counter()
        forecast = forecast_outcomes(context)
        prediction_time = time.perf_counter() - t_pred
        context["forecast"] = forecast
        proposal_text = _draft(context)
        proposal_drafts.append(
            {
                "source": "consolidated",
                "text": proposal_text,
                "context": context,
                "forecast": forecast,
                "prediction_time": prediction_time,
            }
        )
        record_proposal(proposal_text, None, stage="draft")
    try:
        df_pred = pd.DataFrame(
            [
                {
                    "proposal_id": 0,
                    "dao": "Gov",
                    "predicted": "Approved"
                    if forecast.get("approval_prob", 0.0) >= 0.5
                    else "Rejected",
                    "confidence": forecast.get("approval_prob", 0.0),
                    "prediction_time": dt.datetime.now(dt.UTC).isoformat(),
                    "margin_of_error": forecast.get("turnout_estimate", 0.0),
                }
            ]
        )
        eval_res = compare_predictions(df_pred)
        stats["prediction_eval"] = eval_res.get("prediction_eval", [])
    except Exception:
        stats["prediction_eval"] = []
    if not stats["prediction_eval"]:
        stats["prediction_eval"] = evaluate_historical_predictions()
    timestamp = dt.datetime.now(dt.UTC).strftime("%Y%m%d-%H%M%S")
    (OUT_DIR / f"context_{timestamp}.json").write_text(json.dumps(context, indent=2))
    phase_times["analysis_prediction_s"] = time.perf_counter() - t1

    # -------------------------- Draft + Sign ------------------------------
    t2 = time.perf_counter()
    print("🔄 Asking LLM to draft proposal …")
    timestamp = dt.datetime.now(dt.UTC).strftime("%Y%m%d-%H%M%S")
    (OUT_DIR / f"proposal_{timestamp}.txt").write_text(proposal_text)
    broadcast_proposal(proposal_text)

    node_url = os.getenv("SUBSTRATE_NODE_URL", "")
    private_key = os.getenv("SUBSTRATE_PRIVATE_KEY", "")
    track = os.getenv("GOVERNANCE_TRACK", "root")
    referendum_index = 0
    submission_id = None

    if node_url and private_key:
        try:
            preimage_receipt = submit_preimage(
                node_url, private_key, proposal_text.encode("utf-8")
            )
            preimage_hash = preimage_receipt.get("preimage_hash")
            proposal_receipt = submit_proposal(
                node_url, private_key, preimage_hash, track
            )
            submission_id = proposal_receipt.get("extrinsic_hash")
            referendum_index = int(proposal_receipt.get("referendum_index", 0) or 0)
        except Exception:
            submission_id = None
            referendum_index = 0

    record_proposal(proposal_text, None, stage="final")
    record_proposal(proposal_text, submission_id, stage="submitted")
    if submission_id:
        print(f"🔗 Proposal submitted → {submission_id}")
        try:
            block_hash, outcome = await_execution(
                node_url,
                referendum_index,
                submission_id,
            )
        except Exception:
            block_hash, outcome = submission_id, "pending"
        if outcome == "Approved":
            try:
                exec_receipt = execute_proposal(node_url, private_key)
                record_execution_result(
                    status="Executed",
                    block_hash=exec_receipt.get("block_hash", ""),
                    outcome=outcome,
                    submission_id=submission_id,
                    extrinsic_hash=exec_receipt.get("extrinsic_hash", ""),
                    referendum_index=referendum_index,
                )
            except Exception:
                record_execution_result(
                    status="execution_failed",
                    block_hash="",
                    outcome=outcome,
                    submission_id=submission_id,
                    extrinsic_hash="",
                    referendum_index=referendum_index,
                )
        else:
            record_execution_result(
                status=outcome,
                block_hash=block_hash,
                outcome=outcome,
                submission_id=submission_id,
                extrinsic_hash="",
                referendum_index=referendum_index,
            )
    else:
        print("⚠️ Submission failed")
        record_execution_result(
            status="failed",
            block_hash="",
            outcome="error",
            submission_id=None,
            extrinsic_hash="",
        )

    phase_times["draft_sign_s"] = time.perf_counter() - t2

    proposals_processed = max(1, len(stats.get("prediction_eval", [])))
    if proposals_processed < 5:
        scenario_label = "Light Load"
    elif proposals_processed < 20:
        scenario_label = "Medium Load"
    else:
        scenario_label = "High Load"
    run_timings = {
        "scenario": scenario_label,
        "proposals": proposals_processed,
        **phase_times,
    }
    timings_path = PROJECT_ROOT / "data" / "output" / "timings.json"
    try:
        timings_path.parent.mkdir(parents=True, exist_ok=True)
        existing = (
            json.loads(timings_path.read_text()) if timings_path.exists() else []
        )
        existing.append(run_timings)
        timings_history = existing[-3:]
        timings_path.write_text(json.dumps(timings_history, indent=2))
    except Exception:
        timings_history = [run_timings]
    stats["timings"] = timings_history

    duration = (dt.datetime.now(dt.UTC) - start).total_seconds()
    print(
        f"\n✅ Proposal saved → {OUT_DIR / f'proposal_{timestamp}.txt'}   "
        f"(pipeline took {duration:.1f}s)\n"
    )
    print("----------\n" + proposal_text + "\n----------")
    # Display summary tables (Tables 2-5)
    print_data_sources_table(stats.get("data_sources", {}))
    print_sentiment_embedding_table(stats.get("sentiment_batches", []))
    print_draft_forecast_table(
        stats.get("draft_predictions", []), MIN_PASS_CONFIDENCE
    )
    print_prediction_accuracy_table(stats["prediction_eval"])
    print_timing_benchmarks_table(stats.get("timings", []))

if __name__ == "__main__":
    _refresh_workbook()
    main()

