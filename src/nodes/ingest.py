import logging
import os

from github import Auth, Github

from src.github_app_auth import get_github_client
from src.state import PRReviewState

logger = logging.getLogger(__name__)


def fetch_github_diff_node(state: PRReviewState) -> dict:
    """
    Connects to GitHub, fetches the specified PR, and extracts the raw diff.
    Raises ValueError early on missing token or empty diff so the graph
    fails fast rather than running all 4 agents on nothing.
    """
    repo_name = state["repo_name"]
    pr_number = state["pr_number"]

    logger.info(f"Fetching diff for {repo_name} PR #{pr_number}")

    token = os.getenv("GITHUB_TOKEN")
    if not token:
        raise ValueError("GITHUB_TOKEN environment variable is not set.")

    # g    = Github(auth=Auth.Token(token))
    g = get_github_client(repo_name)  # ← use app auth to support any repo with the app installed, rather than just one repo with a PAT
    repo = g.get_repo(repo_name)
    pr   = repo.get_pull(pr_number)

    raw_diff = ""
    for f in pr.get_files():
        if f.patch:
            raw_diff += f"--- {f.filename}\n+++ {f.filename}\n{f.patch}\n\n"

    # FIX: guard against PRs with no reviewable diff (binary files, renames only)
    if not raw_diff.strip():
        raise ValueError(
            f"PR #{pr_number} in {repo_name} has no reviewable text diff. "
            "It may contain only binary changes or file renames."
        )

    logger.info(f"Fetched diff ({len(raw_diff)} chars) for PR #{pr_number}")
    return {
        "raw_diff":         raw_diff,
        "highest_severity": "LOW",   # default; aggregator will update this
    }
