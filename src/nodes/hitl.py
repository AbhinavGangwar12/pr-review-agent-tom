import logging
import os
from github import Auth, Github
from langgraph.types import interrupt
from src.github_app_auth import get_github_client
from src.state import PRReviewState

logger = logging.getLogger(__name__)


# def human_review_node(state: PRReviewState) -> dict:
#     """
#     Triggered only when a CRITICAL issue is detected.
#     Pauses graph execution and waits for a human decision.

#     Resume via:
#         graph.invoke(Command(resume={"approval": "Approve" | "Reject"}), config)
#     """
#     logger.warning("CRITICAL vulnerability detected — halting for human review.")

#     decision = interrupt({
#         "type":         "approval",
#         "message":      "CRITICAL issue detected in PR. Review required before publishing.",
#         "instructions": "Reply with {'approval': 'Approve'} to proceed or {'approval': 'Reject'} to block.",
#         "report":       state.get("final_report", ""),
#     })

#     # FIX: decision is a plain dict returned from Command(resume={...})
#     # Original code used decision.approval (AttributeError) — correct is dict access
#     approval_value = decision.get("approval", "No decision provided") if isinstance(decision, dict) else str(decision)

#     logger.info(f"Human decision received: {approval_value}")

#     return {
#         "review_comments": [{
#             "content":  f"### 👤 Human Review Decision\n**Decision:** {approval_value}",
#             "severity": "CRITICAL",
#         }]
#     }


def human_review_node(state: PRReviewState) -> dict:
    logger.warning("CRITICAL vulnerability detected — halting for human review.")

    # POST ALERT COMMENT BEFORE PAUSING so human can see what was found
    try:
        g    = get_github_client(state["repo_name"])
        repo = g.get_repo(state["repo_name"])
        pr   = repo.get_pull(state["pr_number"])
        pr.create_issue_comment(
            "## ⚠️ CRITICAL Issues Detected — Human Review Required\n\n"
            f"{state.get('final_report', '')}\n\n"
            "---\n"
            "**Action required:** Review the findings above, then submit a PR review:\n"
            "- **Approve** → agent posts the full report and marks complete\n"
            "- **Request changes** → agent blocks the PR"
        )
    except Exception as e:
        logger.error(f"Failed to post HITL alert comment: {e}")

    decision = interrupt({
        "message": "CRITICAL issue detected. Approve or Request Changes on the PR to continue.",
        "report":  state.get("final_report", ""),
    })

    approval_value = decision.get("approval", "Reject") if isinstance(decision, dict) else str(decision)
    logger.info(f"Human decision received: {approval_value}")

    return {
        "review_comments": [{
            "content":  f"### 👤 Human Review Decision\n**Decision:** {approval_value}",
            "severity": "CRITICAL",
        }]
    }



def route_after_aggregator(state: PRReviewState) -> str:
    """
    Routes to human_review_node for CRITICAL issues.
    Routes directly to publish for MEDIUM / LOW.
    """
    severity = state.get("highest_severity", "LOW")
    if severity == "CRITICAL":
        logger.info("Routing to human_review_node (CRITICAL severity detected).")
        return "human_review_node"
    logger.info(f"Routing to post_github_comment_node (severity: {severity}).")
    return "post_github_comment_node"
