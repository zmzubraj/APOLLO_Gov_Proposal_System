"""
main.py
-------
Orchestrator: run the full data pipeline and create a governance proposal
ready to post on Polkadot OpenGov.

Run:
$ python src/main.py
"""

from __future__ import annotations
import json, pathlib, datetime as dt
from data_processing.social_media_scraper import collect_recent_messages
from analysis.sentiment_analysis import analyse_messages
from data_processing.news_fetcher import fetch_and_summarise_news
from data_processing.referenda_updater import update_referenda
# from data_processing.blockchain_data_fetcher import fetch_recent_blocks
from analysis.blockchain_metrics import summarise_blocks, load_blocks_from_file
from analysis.governance_analysis import get_governance_insights
from data_processing.blockchain_cache import get_recent_blocks_cached
from llm.ollama_api import generate_completion
from agents.proposal_submission import submit_proposal
from agents.context_generator import build_context
from execution.discord_bot import post_summary as post_discord
from execution.telegram_bot import post_summary as post_telegram
from execution.twitter_bot import post_summary as post_twitter
from data_processing.proposal_store import (
    record_proposal,
    record_execution_result,
    record_context,
)


# --- main.py  (top of file) -----------------------------------------------
PROJECT_ROOT = pathlib.Path(__file__).resolve().parents[1]  # src/..
OUT_DIR = PROJECT_ROOT / "data" / "output" / "generated_proposals"
OUT_DIR.mkdir(parents=True, exist_ok=True)


def build_prompt(context: dict) -> str:
    """Compose a single prompt for the LLM with all context JSON."""
    return (
        "You are an autonomous Polkadot governance agent. "
        "Draft a concise OpenGov proposal that (1) addresses current community "
        "sentiment and risks, (2) references recent on-chain activity, "
        "(3) aligns with historical governance patterns, and "
        "(4) is formatted for the 'Root' track including Title, Rationale, Action, "
        "and Expected Impact sections.\n\n"
        f"=== CONTEXT (JSON) ===\n{json.dumps(context, indent=2)}\n"
        "======================\n"
        "Return ONLY the proposal text, no JSON."
    )


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
    print("🔄 Collecting social sentiment …")
    msgs = collect_recent_messages()
    # msgs = "Polkadot is pumping hard today 🔥🔥 The new OpenGov referendum looks risky to me. Love the dev updates " \
    #        "from parity! "
    sentiment = analyse_messages(msgs)
    # sentiment = []

    print("🔄 Fetching news …")
    news = fetch_and_summarise_news()
    news = "Polkadot is pumping hard today 🔥🔥 The new OpenGov referendum looks risky to me. Love the dev updates " \
           "from parity! "

    print("🔄 Fetching on-chain data …")
    default_json = pathlib.Path(__file__).resolve().parents[1] / "data" / "output" / "blocks_last3days.json"

    # blocks = load_blocks_from_file(default_json)
    blocks = get_recent_blocks_cached()
    chain_kpis = summarise_blocks(blocks)
    # chain_kpis = []

    print("🔄 Analysing governance history …")
    update_referenda(max_new=500)  # refresh knowledge-base quickly
    gov_kpis = get_governance_insights(as_narrative=True)

    # Bundle context via agent
    context = build_context(sentiment, news, chain_kpis, gov_kpis)
    timestamp = dt.datetime.utcnow().strftime("%Y%m%d-%H%M%S")
    (OUT_DIR / f"context_{timestamp}.json").write_text(json.dumps(context, indent=2))
    record_context(context)

    print("🔄 Asking LLM to draft proposal …")
    proposal_text = generate_completion(
        prompt=build_prompt(context),
        system="You are Polkadot-Gov-Agent v1.",
        model="gemma3:4b",
        temperature=0.3,
        max_tokens=2048,
    )
    timestamp = dt.datetime.utcnow().strftime("%Y%m%d-%H%M%S")
    (OUT_DIR / f"proposal_{timestamp}.txt").write_text(proposal_text)
    broadcast_proposal(proposal_text)
    submission_id = submit_proposal(proposal_text)
    record_proposal(proposal_text, submission_id)
    if submission_id:
        print(f"🔗 Proposal submitted → {submission_id}")
        record_execution_result(
            status="submitted",
            block_hash=submission_id,
            outcome="pending",
            submission_id=submission_id,
        )
    else:
        print("⚠️ Submission failed")
        record_execution_result(
            status="failed",
            block_hash="",
            outcome="error",
            submission_id=None,
        )

    duration = (dt.datetime.utcnow() - start).total_seconds()
    print(f"\n✅ Proposal saved → {OUT_DIR/'proposal_latest.txt'}   "
          f"(pipeline took {duration:.1f}s)\n")
    print("----------\n" + proposal_text + "\n----------")


if __name__ == "__main__":
    main()

