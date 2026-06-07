import os
from langgraph.checkpoint.memory import MemorySaver
from langgraph.graph import END, START, StateGraph
import psycopg
from langgraph.checkpoint.postgres import PostgresSaver

from src.nodes.agents import (
    performance_agent_node,
    security_agent_node,
    style_docs_agent_node,
    test_coverage_agent_node,      # FIX: was missing
)
from src.nodes.aggregator import aggregator_node       # FIX: was importing from wrong path
from src.nodes.hitl import human_review_node, route_after_aggregator
from src.nodes.ingest import fetch_github_diff_node
from src.nodes.publish import post_github_comment_node, reject_node
from src.nodes.report import markdown_report_node  # FIX: was missing, used by human_review_node   
from src.state import PRReviewState

def route_after_hitl(state: PRReviewState) -> str:
    comments = state.get("review_comments", [])
    for c in reversed(comments):
        if "Human Review Decision" in c.get("content", ""):
            if "Reject" in c.get("content", ""):
                return "reject_node"
    return "post_github_comment_node"

def build_review_graph():
    builder = StateGraph(PRReviewState)

    # ── Register nodes ────────────────────────────────────────────────────────
    builder.add_node("fetch_github_diff_node",   fetch_github_diff_node)
    builder.add_node("security_agent_node",      security_agent_node)
    builder.add_node("performance_agent_node",   performance_agent_node)
    builder.add_node("style_docs_agent_node",    style_docs_agent_node)
    builder.add_node("test_coverage_agent_node", test_coverage_agent_node)  # FIX: added
    builder.add_node("aggregator_node",          aggregator_node)
    builder.add_node("human_review_node",        human_review_node)
    builder.add_node("post_github_comment_node", post_github_comment_node)
    builder.add_node("markdown_report_node", markdown_report_node)
    builder.add_node("reject_node", reject_node)

    # ── Ingest → parallel fan-out to all 4 agents ─────────────────────────────
    # LangGraph executes all 4 agents concurrently in the same superstep.
    builder.add_edge(START,                      "fetch_github_diff_node")
    builder.add_edge("fetch_github_diff_node",   "security_agent_node")
    builder.add_edge("fetch_github_diff_node",   "performance_agent_node")
    builder.add_edge("fetch_github_diff_node",   "style_docs_agent_node")
    builder.add_edge("fetch_github_diff_node",   "test_coverage_agent_node")

    # ── Parallel fan-in → aggregator ──────────────────────────────────────────
    # operator.add on review_comments merges all 4 agent outputs into one list.
    builder.add_edge("security_agent_node",      "aggregator_node")
    builder.add_edge("performance_agent_node",   "aggregator_node")
    builder.add_edge("style_docs_agent_node",    "aggregator_node")
    builder.add_edge("test_coverage_agent_node", "aggregator_node")

    # ── Conditional routing: CRITICAL → HITL, else → publish ─────────────────
    builder.add_conditional_edges("aggregator_node", route_after_aggregator, {
        "human_review_node": "human_review_node",
        "post_github_comment_node": "post_github_comment_node"
    })
    builder.add_conditional_edges("human_review_node", route_after_hitl, {
        "post_github_comment_node": "post_github_comment_node",
        "reject_node":              "reject_node",
    })

    # ── Remaining linear paths ────────────────────────────────────────────────
    # builder.add_edge("human_review_node",        "post_github_comment_node")
    # builder.add_edge("post_github_comment_node", END)
    builder.add_edge("post_github_comment_node", "markdown_report_node")
    builder.add_edge("markdown_report_node", END)
    builder.add_edge("reject_node", END)

    conn        = psycopg.connect(os.getenv("DATABASE_URL"), autocommit=True)
    checkpointer = PostgresSaver(conn)
    checkpointer.setup()  # Ensure the necessary table exists

    return builder.compile(checkpointer=checkpointer)
    # return builder.compile() ## Just to generate the graph image without needing a DB connection
