import operator
from typing import Annotated, List, TypedDict


class PRReviewState(TypedDict):
    """
    Global state schema for the PR Review Graph.

    review_comments uses operator.add so parallel agent nodes can each
    append their result without overwriting each other during fan-in.
    """
    repo_name:        str
    pr_number:        int
    raw_diff:         str                                   # FIX: was 'raw_driff'

    review_comments:  Annotated[List[dict], operator.add]

    highest_severity: str
    final_report:     str                                   # FIX: was missing, used by publish.py
    markdown_report_path: str