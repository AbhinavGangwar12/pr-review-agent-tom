import logging
import os

from dotenv import load_dotenv
from fastapi import BackgroundTasks, FastAPI, HTTPException, Request
from langgraph.types import Command
from pydantic import BaseModel

from src.graph import build_review_graph

load_dotenv()
logging.basicConfig(level=logging.INFO, format="%(levelname)s: %(name)s - %(message)s")
logger = logging.getLogger(__name__)

app = FastAPI(title="Multi-Agent PR Reviewer API", version="1.0.0")
review_graph = build_review_graph()


# ── Helpers ───────────────────────────────────────────────────────────────────

def _thread_id(repo_name: str, pr_number: int) -> str:
    return f"pr_{repo_name.replace('/', '_')}_{pr_number}"


def _config(thread_id: str) -> dict:
    return {"configurable": {"thread_id": thread_id}}


# ── Background worker ─────────────────────────────────────────────────────────

def _run_review(repo_name: str, pr_number: int) -> None:
    """
    Worker executed by FastAPI BackgroundTasks.
    Keeps the webhook response under GitHub's 10-second timeout.

    If the graph hits an interrupt() (CRITICAL severity), it pauses here and
    persists state to MemorySaver. A human then calls POST /resume/{thread_id}
    to continue — that endpoint resumes the same thread.
    """
    tid = _thread_id(repo_name, pr_number)
    logger.info(f"Background review started → thread: {tid}")

    initial_state = {
        "repo_name":       repo_name,
        "pr_number":       pr_number,
        "review_comments": [],
    }
    try:
        review_graph.invoke(initial_state, _config(tid))
        logger.info(f"Review complete for thread: {tid}")
    except Exception as e:
        logger.error(f"Review failed for thread {tid}: {e}")


# ── Webhook endpoint ──────────────────────────────────────────────────────────

# @app.post("/webhook")
# async def github_webhook(request: Request, background_tasks: BackgroundTasks):
#     """
#     Entry point for GitHub PR webhooks.
#     Configure your repo's webhook to send 'pull_request' events here.
#     """
#     try:
#         payload = await request.json()
#     except Exception:
#         raise HTTPException(status_code=400, detail="Invalid JSON payload.")

#     if "pull_request" not in payload:
#         return {"status": "ignored", "detail": "Not a pull_request event."}

#     action = payload.get("action")
#     if action not in ("opened", "synchronize"):
#         return {"status": "ignored", "detail": f"Action '{action}' not targeted."}

#     repo_name = payload["repository"]["full_name"]
#     pr_number = payload["pull_request"]["number"]
#     tid       = _thread_id(repo_name, pr_number)

#     logger.info(f"PR event '{action}' received → {repo_name} #{pr_number}")
#     background_tasks.add_task(_run_review, repo_name, pr_number)

#     return {"status": "accepted", "thread_id": tid, "detail": "Review initiated."}


# ── HITL resume endpoint ──────────────────────────────────────────────────────
# FIX: this was missing from the original code.
# When a CRITICAL issue pauses the graph, a human must call this endpoint
# to provide their decision and resume execution.

class ResumePayload(BaseModel):
    approval: str   # "Approve" or "Reject"


@app.post("/resume/{thread_id}")
async def resume_review(thread_id: str, body: ResumePayload, background_tasks: BackgroundTasks):
    """
    Resume a graph that was paused at a CRITICAL human-review interrupt.

    Example:
        POST /resume/pr_owner_repo_42
        {"approval": "Approve"}
    """
    logger.info(f"Resume requested for thread '{thread_id}' with decision: {body.approval}")

    def _resume():
        try:
            review_graph.invoke(
                Command(resume={"approval": body.approval}),
                _config(thread_id),
            )
            logger.info(f"Graph resumed and completed for thread: {thread_id}")
        except Exception as e:
            logger.error(f"Resume failed for thread {thread_id}: {e}")

    background_tasks.add_task(_resume)
    return {"status": "resuming", "thread_id": thread_id, "decision": body.approval}


# ── Status endpoint ───────────────────────────────────────────────────────────

@app.get("/status/{thread_id}")
async def review_status(thread_id: str):
    """
    Returns the current persisted state for a given thread.
    Useful for checking if a review is paused, complete, or still running.
    """
    state = review_graph.get_state(_config(thread_id))
    if state is None:
        raise HTTPException(status_code=404, detail=f"No state found for thread '{thread_id}'.")

    next_nodes = list(state.next) if state.next else []
    return {
        "thread_id":        thread_id,
        "next":             next_nodes,
        "is_paused":        bool(next_nodes),
        "highest_severity": state.values.get("highest_severity", "unknown"),
    }


@app.post("/webhook")
async def github_webhook(request: Request, background_tasks: BackgroundTasks):
    payload    = await request.json()
    event_type = request.headers.get("X-GitHub-Event", "")

    # ── New PR or push to PR → start review ──────────────────────────────
    if event_type == "pull_request":
        action = payload.get("action")
        if action not in ("opened", "synchronize"):
            return {"status": "ignored"}
        repo_name = payload["repository"]["full_name"]
        pr_number = payload["pull_request"]["number"]
        background_tasks.add_task(_run_review, repo_name, pr_number)
        return {"status": "accepted"}

    # ── Human approved/rejected via GitHub UI → resume HITL ──────────────
    if event_type == "pull_request_review":
        if payload.get("action") != "submitted":
            return {"status": "ignored"}
        review_state = payload["review"]["state"]          # "approved" / "changes_requested"
        repo_name    = payload["repository"]["full_name"]
        pr_number    = payload["pull_request"]["number"]
        tid          = _thread_id(repo_name, pr_number)
        approval     = "Approve" if review_state == "approved" else "Reject"

        def _resume():
            review_graph.invoke(Command(resume={"approval": approval}), _config(tid))

        background_tasks.add_task(_resume)
        return {"status": "resumed", "decision": approval}
    
    if event_type == "issue_comment":
        if payload.get("action") != "created":
            return {"status": "ignored"}

        body      = payload.get("comment", {}).get("body", "").strip().lower()
        repo_name = payload["repository"]["full_name"]
        pr_number = payload.get("issue", {}).get("number")

        if not pr_number or body not in ("/approve", "/reject"):
            return {"status": "ignored"}

        tid      = _thread_id(repo_name, pr_number)
        approval = "Approve" if body == "/approve" else "Reject"

        def _resume():
            review_graph.invoke(Command(resume={"approval": approval}), _config(tid))

        background_tasks.add_task(_resume)
        return {"status": "resumed", "decision": approval}

    return {"status": "ignored"}

# ── Health check ──────────────────────────────────────────────────────────────

@app.get("/health")
async def health():
    return {"status": "ok"}


# debug
@app.get("/debug/auth")
async def debug_auth():
    import os
    from github import Auth, GithubIntegration
    try:
        app_id      = os.getenv("GITHUB_APP_ID")
        private_key = os.getenv("GITHUB_APP_PRIVATE_KEY").replace("\\n", "\n")
        integration = GithubIntegration(auth=Auth.AppAuth(int(app_id), private_key))
        installations = list(integration.get_installations())
        return {"status": "ok", "app_id": app_id, "installations": len(installations)}
    except Exception as e:
        return {"status": "error", "detail": str(e)}
