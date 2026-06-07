import logging

from src.state import PRReviewState

logger = logging.getLogger(__name__)

# Severity ranking — higher index = more severe
_SEVERITY_RANK = {"LOW": 0, "MEDIUM": 1, "CRITICAL": 2}


def aggregator_node(state: PRReviewState) -> dict:
    """
    Collects all parallel reviews, computes the overall highest severity,
    and formats a single Markdown report for the publish node.

    Severity resolution: takes the maximum severity across all agent outputs.
    """
    logger.info("Aggregating agent reviews...")

    comments        = state.get("review_comments", [])
    highest_rank    = 0
    highest_sev     = "LOW"

    for comment in comments:
        sev  = comment.get("severity", "LOW").upper()
        rank = _SEVERITY_RANK.get(sev, 0)
        if rank > highest_rank:
            highest_rank = rank
            highest_sev  = sev

    if not comments:
        final_report = "_No review comments were generated._"
    else:
        sections     = [c.get("content", "") for c in comments]
        severity_badge = {
            "LOW":      "🟢 LOW",
            "MEDIUM":   "🟡 MEDIUM",
            "CRITICAL": "🔴 CRITICAL",
        }.get(highest_sev, highest_sev)

        final_report = (
            f"**Overall Severity:** {severity_badge}\n\n"
            + "\n\n---\n\n".join(sections)
        )

    logger.info(f"Aggregation complete. Highest severity: {highest_sev}")
    return {
        "highest_severity": highest_sev,
        "final_report":     final_report,
    }
