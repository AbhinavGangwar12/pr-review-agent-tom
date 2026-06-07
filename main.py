"""
Local test runner for the PR Review graph.
Triggers a real GitHub PR review via the terminal with HITL support.

Usage:
    python main.py

Set REPO_NAME and TEST_PR_NUMBER below before running.
"""

import os

from dotenv import load_dotenv
from langgraph.types import Command

from src.graph import build_review_graph

load_dotenv()

REPO_NAME      = "AbhinavGangwar12/pr-reviewer-sandbox"   # ← change this
TEST_PR_NUMBER = 1      # ← change this


if __name__ == "__main__":
    graph  = build_review_graph()
    tid    = f"pr_review_{TEST_PR_NUMBER}"
    config = {"configurable": {"thread_id": tid}}

    initial_state = {
        "repo_name":       REPO_NAME,
        "pr_number":       TEST_PR_NUMBER,
        "review_comments": [],
    }

    print(f"\n{'='*60}")
    print(f"  PR Reviewer — thread: {tid}")
    print(f"{'='*60}\n")

    # ── Step 1: stream the graph until it finishes or interrupts ──────────────
    for event in graph.stream(initial_state, config, stream_mode="updates"):
        node_name = list(event.keys())[0]
        if node_name != "__interrupt__":
            print(f"✅ {node_name} complete")

        if "__interrupt__" in event:
            interrupt_data = event["__interrupt__"][0].value
            print(f"\n{'='*60}")
            print("🛑  EXECUTION PAUSED — CRITICAL ISSUE DETECTED")
            print(f"{'='*60}")
            print(f"\nMessage  : {interrupt_data.get('message')}")
            print(f"Instructions: {interrupt_data.get('instructions')}")
            print("\n--- Report Preview ---")
            print(interrupt_data.get("report", "")[:500])
            print(f"{'='*60}\n")

            # ── Step 2: collect human decision ───────────────────────────────
            user_input = input("Enter decision (Approve / Reject): ").strip()
            if not user_input:
                user_input = "Reject"

            print("\nResuming graph...\n")

            # ── Step 3: resume with Command ───────────────────────────────────
            for resume_event in graph.stream(
                Command(resume={"approval": user_input}),
                config,
                stream_mode="updates",
            ):
                node_name = list(resume_event.keys())[0]
                print(f"✅ {node_name} complete")

    print(f"\n{'='*60}")
    print("  Review complete.")
    print(f"{'='*60}\n")
