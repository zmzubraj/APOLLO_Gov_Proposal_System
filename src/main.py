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
from agents.data_collector import DataCollector
from data_processing.social_media_scraper import collect_recent_messages
from reporting.summary_tables import (
    print_data_sources_table,
    print_sentiment_embedding_table,
    print_prediction_accuracy_table,
    print_timing_benchmarks_table,
)
from agents.sentiment_analyser import analyse_messages
from data_processing.news_fetcher import fetch_and_summarise_news
from data_processing.referenda_updater import update_referenda
# from data_processing.blockchain_data_fetcher import fetch_recent_blocks
from data_processing.blockchain_cache import get_recent_blocks_cached
from analysis.blockchain_metrics import summarise_blocks
from analysis.governance_analysis import get_governance_insights
from agents.outcome_forecaster import forecast_outcomes
from analysis.prediction_evaluator import compare_predictions
from agents import proposal_generator
from agents.context_generator import build_context
from llm import ollama_api
from execution.discord_bot import post_summary as post_discord
from execution.telegram_bot import post_summary as post_telegram
from execution.twitter_bot import post_summary as post_twitter
from execution.governor_interface import (
    await_execution,
    execute_proposal,
    submit_preimage,
    submit_proposal,
)
from data_processing.proposal_store import (
    record_proposal,
    record_execution_result,
)


# --- main.py  (top of file) -----------------------------------------------
PROJECT_ROOT = pathlib.Path(__file__).resolve().parents[1]  # src/..
OUT_DIR = PROJECT_ROOT / "data" / "output" / "generated_proposals"
OUT_DIR.mkdir(parents=True, exist_ok=True)


def broadcast_proposal(text: str) -> None:
    """Send ``text`` to any configured community platforms."""
    sent = []
    if post_discord(text):
        sent.append("Discord")
    if post_telegram(text):
        sent.append("Telegram")
    if post_twitter(text):
        sent.append("Twitter")
    if sent:
        print("📢 Broadcasted proposal to " + ", ".join(sent))
    else:
        print("⚠️ No community platforms configured")
def main() -> None:
    start = dt.datetime.now(dt.UTC)
    stats: dict[str, Any] = {}
    phase_times: dict[str, float] = {}

    # ------------------------------ Ingestion ------------------------------
    t0 = time.perf_counter()
    data = DataCollector.collect(
        collect_recent_messages,
        fetch_and_summarise_news,
        get_recent_blocks_cached,
        stats=stats,
    )
    phase_times["ingestion_s"] = time.perf_counter() - t0

    msgs_by_source = data["messages"]
    stats.setdefault("sentiment_batches", [])

    # ----------------------- Analysis + Prediction ------------------------
    t1 = time.perf_counter()
    batch_id = 1
    all_msgs: list[str] = []
    for source, msgs in msgs_by_source.items():
        all_msgs.extend(msgs)
        res = analyse_messages(msgs)
        raw_text = "\n".join(msgs).strip()
        ctx_size = res.get(
            "message_size_kb",
            len(raw_text.encode("utf-8")) / 1024 if raw_text else 0.0,
        )
        try:
            ollama_api.embed_text(raw_text)
            embedded = True
        except Exception:
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
    sentiment = analyse_messages(all_msgs) if all_msgs else {}
    # sentiment = []

    news = data["news"]

    blocks = data["blocks"]
    chain_kpis = summarise_blocks(blocks)
    # chain_kpis = []

    print("🔄 Analysing governance history …")
    update_referenda(max_new=1500)  # refresh knowledge-base quickly
    gov_kpis = get_governance_insights(as_narrative=True)

    # Bundle context via agent including semantic KB retrieval
    keywords = gov_kpis.get("top_keywords", []) if isinstance(gov_kpis, dict) else []
    query = " ".join(keywords[:3])
    context = build_context(
        sentiment,
        news,
        chain_kpis,
        gov_kpis,
        kb_query=query,
        summarise_snippets=True,
    )
    forecast = forecast_outcomes(context)
    context["forecast"] = forecast
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
    timestamp = dt.datetime.now(dt.UTC).strftime("%Y%m%d-%H%M%S")
    (OUT_DIR / f"context_{timestamp}.json").write_text(json.dumps(context, indent=2))
    phase_times["analysis_prediction_s"] = time.perf_counter() - t1

    # -------------------------- Draft + Sign ------------------------------
    t2 = time.perf_counter()
    print("🔄 Asking LLM to draft proposal …")
    proposal_text = proposal_generator.draft(context)
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

    record_proposal(proposal_text, submission_id)
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
        scenario = "light"
    elif proposals_processed < 20:
        scenario = "medium"
    else:
        scenario = "high"
    stats["timings"] = {
        scenario: {
            "proposals": proposals_processed,
            **phase_times,
        }
    }
    timings_path = PROJECT_ROOT / "data" / "output" / "timings.json"
    try:
        timings_path.parent.mkdir(parents=True, exist_ok=True)
        existing = (
            json.loads(timings_path.read_text()) if timings_path.exists() else {}
        )
        existing.setdefault(scenario, []).append(stats["timings"][scenario])
        timings_path.write_text(json.dumps(existing, indent=2))
    except Exception:
        pass

    duration = (dt.datetime.now(dt.UTC) - start).total_seconds()
    print(
        f"\n✅ Proposal saved → {OUT_DIR / f'proposal_{timestamp}.txt'}   "
        f"(pipeline took {duration:.1f}s)\n"
    )
    print("----------\n" + proposal_text + "\n----------")
    # Display summary tables (Tables 2-5)
    print_data_sources_table(stats.get("data_sources", {}))
    print_sentiment_embedding_table(stats.get("sentiment_batches", []))
    print_prediction_accuracy_table(stats.get("prediction_eval", []))
    print_timing_benchmarks_table(stats.get("timings", {}))

if __name__ == "__main__":
    main()

