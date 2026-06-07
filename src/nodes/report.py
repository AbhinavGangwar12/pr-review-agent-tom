import logging
import os
from datetime import datetime

from langchain_core.messages import HumanMessage

from src.config import get_llm
from src.state import PRReviewState

logger = logging.getLogger(__name__)

def markdown_report_node(state: PRReviewState) -> dict:
    """
    Uses the LLM to format the aggregated review into a polished Markdown report
    and saves it to the reviews/ directory. 
    
    Example output path: reviews/ser_duncan_the_tall_api_pr4_20260607.md
    """
    logger.info("Generating Markdown report...")
    llm = get_llm()
    
    repo_name = state["repo_name"]
    pr_number = state["pr_number"]
    severity  = state.get("highest_severity", "LOW")
    report    = state.get("final_report", "")
    
    prompt = f"""
You are a technical writer, bringing the diligence, honor, and straightforward clarity of Ser Duncan the Tall to your documentation. Format the following code review data into a polished, well-structured Markdown report.

Repository: {repo_name}
PR Number: #{pr_number}
Overall Severity: {severity}
Review Date: {datetime.now().strftime("%Y-%m-%d %H:%M UTC")}

Raw Review Data:
{report}

Generate a professional Markdown report with:
1. A header with repo, PR number, date, and severity badge.
2. An executive summary (2-3 sentences).
3. Individual sections for each agent's findings.
4. A prioritized recommendations section.
5. A footer.

Use proper Markdown formatting: headers, bold, code blocks where relevant, and emoji severity indicators.
Return ONLY the Markdown content, nothing else.
"""
    
    response = llm.invoke([HumanMessage(content=prompt)])
    markdown_content = response.content
    
    # Save to file
    os.makedirs("reviews", exist_ok=True)
    timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
    safe_repo = repo_name.replace("/", "_")
    filename  = f"reviews/{safe_repo}_pr{pr_number}_{timestamp}.md"
    
    with open(filename, "w", encoding="utf-8") as f:
        f.write(markdown_content)
    
    logger.info(f"Markdown report saved → {filename}")
    return {"markdown_report_path": filename}