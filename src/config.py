import logging
import os
from dotenv import load_dotenv

load_dotenv()

import httpx
# from langchain_ollama import ChatOllama
from langchain_groq import ChatGroq

logging.basicConfig(level=logging.INFO, format="%(levelname)s: %(name)s - %(message)s")
logger = logging.getLogger(__name__)

# ── LangSmith tracing ─────────────────────────────────────────────────────────
# Set LANGCHAIN_API_KEY in your .env. The two lines below activate auto-tracing
# for every LangGraph node: token counts, latency, inputs/outputs, all visible
# in the LangSmith dashboard without any additional instrumentation code.
os.environ.setdefault("LANGCHAIN_TRACING_V2", "true")
os.environ.setdefault("LANGCHAIN_PROJECT", "pr-reviewer-multi-agent")
# ─────────────────────────────────────────────────────────────────────────────


def get_llm() -> ChatGroq: #ChatOllama
    """
    Initialize and return the LLM.
    Swap ChatOllama for ChatOpenAI / ChatGroq here if you move off local inference.
    """
    try:
        api_key = os.getenv("GROQ_API_KEY")
        if not api_key:
            raise ValueError("GROQ_API_KEY not set.")
        llm = ChatGroq(
            model="llama-3.3-70b-versatile",
            temperature=0.1,
            api_key=api_key,
        )
        # llm = ChatOllama(
        #     model="mistral",
        #     temperature=0.1,
        #     client_kwargs={"timeout": httpx.Timeout(120.0)},
        # )
        return llm
    except Exception as e:
        logger.error(f"Failed to connect to local Ollama instance: {e}")
        raise
