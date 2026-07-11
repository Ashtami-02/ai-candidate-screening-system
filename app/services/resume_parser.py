"""
Resume parsing: PDF or plain text -> structured JSON of skills/tech/domains.

Why use the LLM for this instead of keyword matching? A resume might say
"built classification models" without ever writing the word "scikit-learn"
literally next to "machine learning" -- an LLM reading for meaning catches
this; a hardcoded keyword list wouldn't.
"""

import json
from pathlib import Path

from app.services.llm_client import generate
from app.services.rag.ingest import extract_text_from_pdf

EXTRACTION_PROMPT = """You are analyzing a candidate's resume for a technical interview system.

Read the resume text below and extract the following, based ONLY on what is
actually stated or clearly implied in the text -- do not invent skills that
aren't there.

IMPORTANT LIMITS (the candidate's resume may list many things -- pick only
the MOST significant/relevant ones, do not list everything):
- "skills": at most 8 items, the most important ones
- "technologies": at most 8 items
- "domains": at most 5 items
- "notable_projects": at most 4 items, each a SHORT one-sentence description

Return ONLY valid JSON (no markdown formatting, no explanation, no code
fences) in exactly this structure:

{{
  "skills": ["list", "of", "technical skills"],
  "technologies": ["list", "of", "tools/frameworks/languages"],
  "domains": ["list", "of", "domain areas like NLP, computer vision, backend systems"],
  "experience_level": "entry-level | intermediate | experienced",
  "notable_projects": ["short one-sentence description of each major project"]
}}

Resume text:
---
{resume_text}
---
"""


def extract_resume_text(file_path: str) -> str:
    """Handles both PDF and plain .txt resumes, per the assignment spec."""
    path = Path(file_path)
    if path.suffix.lower() == ".pdf":
        return extract_text_from_pdf(file_path)
    else:
        return path.read_text(encoding="utf-8", errors="ignore")


def _clean_json_response(raw_text: str) -> str:
    """
    LLMs frequently wrap JSON in markdown code fences (```json ... ```)
    even when explicitly told not to. Strip that defensively rather than
    trusting the prompt alone -- prompts are guidance, not guarantees.
    """
    text = raw_text.strip()
    if text.startswith("```"):
        text = text.split("```")[1]
        text = text.removeprefix("json").strip()
    return text.strip()


def parse_resume(file_path: str) -> dict:
    resume_text = extract_resume_text(file_path)
    prompt = EXTRACTION_PROMPT.format(resume_text=resume_text)

    # Try increasingly generous token budgets. The Gemini 2.5 model family
    # spends some of its budget on internal reasoning before writing the
    # visible answer, so even a seemingly generous cap can still truncate
    # mid-JSON. Rather than guess one "safe" number, retry with more room
    # if the previous attempt didn't produce valid, complete JSON.
    token_budgets = [3000, 6000, 10000]
    last_error = None
    last_raw_response = None

    for budget in token_budgets:
        raw_response = generate(prompt, max_output_tokens=budget)
        cleaned = _clean_json_response(raw_response)
        try:
            return json.loads(cleaned)
        except json.JSONDecodeError as e:
            last_error = e
            last_raw_response = raw_response
            continue  # try again with a bigger budget

    # If every attempt failed, surface the raw text -- this makes debugging
    # much easier than a bare crash, since you can SEE what the model
    # actually returned and adjust the prompt accordingly.
    raise ValueError(
        f"Could not parse LLM response as JSON after {len(token_budgets)} attempts.\n"
        f"Last error: {last_error}\nLast raw response:\n{last_raw_response}"
    )


if __name__ == "__main__":
    import sys

    resume_path = sys.argv[1] if len(sys.argv) > 1 else "data/knowledge_base/sample_resume.pdf"
    result = parse_resume(resume_path)
    print(json.dumps(result, indent=2))
