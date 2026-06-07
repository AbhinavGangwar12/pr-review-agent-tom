import logging

from langchain_core.messages import HumanMessage
from pydantic import BaseModel, Field

from src.config import get_llm
from src.state import PRReviewState

logger = logging.getLogger(__name__)
llm = get_llm()


# ── Shared output schema ───────────────────────────────────────────────────────

class ReviewComment(BaseModel):
    """Structured output contract for every review agent."""
    content:  str = Field(..., description="The review comment body.")
    severity: str = Field(
        "LOW",
        description="Severity of the finding: LOW, MEDIUM, or CRITICAL.",
    )


# ── Agent nodes ───────────────────────────────────────────────────────────────

def security_agent_node(state: PRReviewState) -> dict:
    """
    Scans the diff for security vulnerabilities:
    injection flaws, hardcoded secrets, unsafe dependencies, privilege escalation.
    """
    logger.info("Security Agent analyzing diff...")
    prompt = (
        "You are a strict security auditor. Analyze the following code diff for:\n"
        "- Injection flaws (SQL, command, path traversal)\n"
        "- Hardcoded secrets, API keys, or passwords\n"
        "- Use of unsafe or deprecated library calls\n"
        "- Privilege escalation risks\n\n"
        "Return severity as CRITICAL if any finding could directly compromise the system, "
        "MEDIUM for indirect risks, LOW for minor concerns.\n\n"
        f"diff:\n{state['raw_diff']}"  # FIX: was raw_driff
    )
    response = llm.with_structured_output(ReviewComment).invoke([HumanMessage(content=prompt)])
    return {
        "review_comments": [{
            "content":  f"### 🔒 Security Review\n{response.content}",
            "severity": response.severity,
        }]
    }


def performance_agent_node(state: PRReviewState) -> dict:
    """
    Scans the diff for runtime inefficiencies, memory leaks,
    N+1 query patterns, and unoptimized loops.
    """
    logger.info("Performance Agent analyzing diff...")
    prompt = (
        "You are a performance engineer. Analyze the following code diff for:\n"
        "- N+1 database query patterns\n"
        "- Unnecessary loops or recomputation inside loops\n"
        "- Memory leaks or unbounded data structures\n"
        "- Blocking I/O in async contexts\n\n"
        "Return severity as CRITICAL for issues that will cause outages under load, "
        "MEDIUM for significant slowdowns, LOW for minor inefficiencies.\n\n"
        f"diff:\n{state['raw_diff']}"
    )
    response = llm.with_structured_output(ReviewComment).invoke([HumanMessage(content=prompt)])
    return {
        "review_comments": [{
            "content":  f"### ⚡ Performance Review\n{response.content}",
            "severity": response.severity,
        }]
    }


def style_docs_agent_node(state: PRReviewState) -> dict:
    """
    Scans the diff for PEP8 violations, naming conventions,
    and missing or inadequate docstrings.
    """
    logger.info("Style & Docs Agent analyzing diff...")
    prompt = (
        "You are a code quality enforcer. Analyze the following diff for:\n"
        "- PEP8 violations (line length, naming, spacing)\n"
        "- Missing docstrings on public functions and classes\n"
        "- Unclear variable names or magic numbers\n"
        "- Dead code or commented-out blocks\n\n"
        "Return severity as MEDIUM for widespread issues that hurt maintainability, "
        "LOW for isolated style nits.\n\n"
        f"diff:\n{state['raw_diff']}"
    )
    response = llm.with_structured_output(ReviewComment).invoke([HumanMessage(content=prompt)])
    return {
        "review_comments": [{
            "content":  f"### 📝 Style & Docs Review\n{response.content}",
            "severity": response.severity,
        }]
    }


def test_coverage_agent_node(state: PRReviewState) -> dict:
    """
    FIX: was missing from original code.
    Scans the diff for untested code paths, missing edge-case tests,
    and new functions introduced without corresponding test additions.
    """
    logger.info("Test Coverage Agent analyzing diff...")
    prompt = (
        "You are a QA engineer focused on test coverage. Analyze the following diff for:\n"
        "- New functions or methods added without corresponding unit tests\n"
        "- Missing edge-case coverage (empty inputs, boundary values, error paths)\n"
        "- Deleted tests that are not replaced\n"
        "- Assertions that are too broad or trivially pass\n\n"
        "Return severity as CRITICAL if core business logic is entirely untested, "
        "MEDIUM if coverage gaps are significant, LOW for minor missing cases.\n\n"
        f"diff:\n{state['raw_diff']}"
    )
    response = llm.with_structured_output(ReviewComment).invoke([HumanMessage(content=prompt)])
    return {
        "review_comments": [{
            "content":  f"### 🧪 Test Coverage Review\n{response.content}",
            "severity": response.severity,
        }]
    }
