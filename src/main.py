"""
main.py
-------
Orchestrator: run the full data pipeline and create a governance proposal
ready to post on Polkadot OpenGov.

Run:
$ python src/main.py
"""

from __future__ import annotations
import json, pathlib, datetime as dt, os
from agents.data_collector import DataCollector
from data_processing.social_media_scraper import collect_recent_messages
from agents.sentiment_analyser import analyse_messages
from data_processing.news_fetcher import fetch_and_summarise_news
from data_processing.referenda_updater import update_referenda
# from data_processing.blockchain_data_fetcher import fetch_recent_blocks
from data_processing.blockchain_cache import get_recent_blocks_cached
from analysis.blockchain_metrics import summarise_blocks
from analysis.governance_analysis import get_governance_insights
from agents.outcome_forecaster import forecast_outcomes
from agents import proposal_generator
from agents.context_generator import build_context
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
    start = dt.datetime.utcnow()
    data = DataCollector.collect(
        collect_recent_messages,
        fetch_and_summarise_news,
        get_recent_blocks_cached,
    )

    msgs = data["messages"]
    sentiment = analyse_messages(msgs)
    # sentiment = []

    news = data["news"]

    blocks = data["blocks"]
    chain_kpis = summarise_blocks(blocks)
    # chain_kpis = []

    print("🔄 Analysing governance history …")
    update_referenda(max_new=500)  # refresh knowledge-base quickly
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
    timestamp = dt.datetime.utcnow().strftime("%Y%m%d-%H%M%S")
    (OUT_DIR / f"context_{timestamp}.json").write_text(json.dumps(context, indent=2))

    print("🔄 Asking LLM to draft proposal …")
    proposal_text = proposal_generator.draft(context)
    timestamp = dt.datetime.utcnow().strftime("%Y%m%d-%H%M%S")
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
                )
            except Exception:
                record_execution_result(
                    status="execution_failed",
                    block_hash="",
                    outcome=outcome,
                    submission_id=submission_id,
                    extrinsic_hash="",
                )
        else:
            record_execution_result(
                status=outcome,
                block_hash=block_hash,
                outcome=outcome,
                submission_id=submission_id,
                extrinsic_hash="",
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

    duration = (dt.datetime.utcnow() - start).total_seconds()
    print(f"\n✅ Proposal saved → {OUT_DIR/'proposal_latest.txt'}   "
          f"(pipeline took {duration:.1f}s)\n")
    print("----------\n" + proposal_text + "\n----------")


if __name__ == "__main__":
    main()

