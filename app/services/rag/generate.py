"""
Question generation: the "AG" (Augmented Generation) half of RAG.

Pipeline for one question:
  pick an unasked topic from the resume
  -> retrieve textbook chunks about that topic
  -> ask the LLM to write ONE grounded, non-generic question

This is the piece the assignment weighs heaviest, because it's where
retrieval, resume data, and generation actually meet.
"""

from typing import Dict, List

from app.services.llm_client import generate
from app.services.rag.retrieve import retrieve_relevant_chunks_batch

ADAPTIVE_NOTE_TEMPLATE = """
The candidate's previous answer, for your calibration only:
"{previous_answer}"

If that answer was thin, vague, or avoided real depth, make this next
question more foundational to check basic understanding. If it was
detailed and confident, make this one a harder follow-up that pushes
further. You may reference something specific they said if it flows
naturally, but never use a formulaic phrase like "Building on your
previous answer" or "Following up on that."
"""

SHARED_RULES = """
CRITICAL RULES:
1. Never reference the source material. Do NOT say "the textbook," "the
   context," "the text," "according to the material," or anything similar.
   A real interviewer speaks from their own knowledge -- they never cite
   where they read something.
2. Maximum 30 words, ONE sentence. Ask exactly one thing.
3. Avoid generic, dictionary-definition-style questions like "What is
   {topic}?" -- be specific enough that a candidate without real
   understanding couldn't answer from a definition alone.

Return ONLY the question text. No preamble, no explanation, no numbering,
no quotation marks around it.
"""

PERSONALIZED_PROMPT = (
    """You are an experienced technical interviewer conducting a live interview for a {role} position.

Candidate background:
- Skills: {skills}
- Technologies: {technologies}
- Notable projects: {projects}

Background knowledge on the topic of "{topic}" (for you only, never mention
it exists):
---
{context}
---
{adaptive_note}
Generate exactly ONE interview question about "{topic}" that connects
naturally to the candidate's stated experience above.

Never open with a formulaic preamble like "Considering your work on X,"
"Given your experience with Y," or "Based on your project Z." A real
interviewer doesn't announce that they're about to reference your
background -- the connection should feel like a natural, direct question.

Example of a BAD question (formulaic opener, cites source):
"Given the textbook's emphasis on algorithms that improve automatically
through experience, and considering your work on a language detection
model using Naive Bayes, how would you evaluate whether your model's
'experience' was being used effectively, especially with noisy data?"

Example of a GOOD question (natural, direct, still personalized):
"Your language detection model used Naive Bayes -- what would you check
first if its accuracy suddenly dropped on new, messier input data?"
"""
    + SHARED_RULES
)

GENERAL_PROMPT = (
    """You are an experienced technical interviewer conducting a live interview for a {role} position.

Background knowledge on the topic of "{topic}" (for you only, never mention
it exists):
---
{context}
---
{adaptive_note}
Generate exactly ONE interview question that tests genuine conceptual or
applied understanding of "{topic}". Do NOT reference the candidate's resume,
projects, or personal experience at all -- ask about the concept itself, as
you would to any candidate, regardless of their specific background.

Example of a GOOD question:
"When would you choose a generative model over a discriminative one for a
classification task, and what's the tradeoff?"
"""
    + SHARED_RULES
)


def select_best_topic(resume_data: Dict, role: str, asked_topics: List[str]) -> tuple:
    """
    Instead of picking a resume topic at random, check the knowledge base's
    actual coverage for every remaining candidate and pick whichever one
    the KB supports best (lowest retrieval distance = closest match).

    This is what fixes the "Backend systems" problem: if a resume skill
    isn't well covered by this role's knowledge base, its best-match
    distance will be high, so it naturally loses out to a skill the KB
    actually has good content for -- no hardcoded per-role skill list needed.

    Uses batch retrieval (one embedding call, one DB query for ALL
    candidates at once) rather than checking each one individually --
    this is what keeps "start interview" fast even with a long resume.

    Returns (topic, chunks) so the caller can reuse these chunks directly
    instead of retrieving a second time.
    """
    candidates = resume_data.get("skills", []) + resume_data.get("domains", [])
    remaining = [c for c in candidates if c not in asked_topics]

    if not remaining:
        return None, None

    batch_results = retrieve_relevant_chunks_batch(remaining, role, top_k=3)

    scored_candidates = []
    for topic, chunks in zip(remaining, batch_results):
        best_distance = chunks[0]["distance"] if chunks else float("inf")
        scored_candidates.append((best_distance, topic, chunks))

    # Lowest distance = best semantic match = most content in the KB
    scored_candidates.sort(key=lambda item: item[0])
    _best_distance, best_topic, best_chunks = scored_candidates[0]
    return best_topic, best_chunks


INSIGHTS_PROMPT = """You are reviewing a completed technical interview transcript for a {role} candidate.

Transcript:
{transcript}

Write a brief analysis (3-4 sentences) covering:
- Which topics the candidate engaged with most confidently
- Any notable strength shown in their answers
- One area that seemed thinner or worth probing further in a follow-up round

Base this ONLY on what's actually in the transcript above -- do not invent
detail that isn't there. If an answer was very short or empty, that itself
is worth noting rather than glossing over.

Write in a neutral, professional tone, as a hiring note for another
interviewer to read. Return ONLY the analysis text, no headers or preamble.
"""


def generate_session_insights(qa_pairs: List[Dict], role: str) -> str:
    """
    One LLM call, run once at the END of a session (not per-question), that
    reads the full transcript and produces a short qualitative summary.
    This is what satisfies the assignment's "provide basic insights or
    analysis of the session" requirement -- a plain list of Q&A pairs
    alone doesn't count as analysis.
    """
    answered_pairs = [qa for qa in qa_pairs if qa.get("answer")]
    if not answered_pairs:
        return "No questions were answered, so no analysis is available for this session."

    transcript_lines = []
    for i, qa in enumerate(answered_pairs, 1):
        transcript_lines.append(f"Q{i} ({qa.get('topic', 'general')}): {qa['question']}")
        transcript_lines.append(f"A{i}: {qa['answer']}")
    transcript = "\n".join(transcript_lines)

    prompt = INSIGHTS_PROMPT.format(role=role, transcript=transcript)
    return generate(prompt).strip()


def _looks_truncated(text: str) -> bool:
    """A properly finished question should end in real punctuation. If it
    doesn't, the response was almost certainly cut off mid-sentence."""
    return not text.rstrip().endswith((".", "?", "!", '"'))


def generate_question(
    resume_data: Dict,
    role: str,
    asked_topics: List[str] = None,
    previous_answer: str = None,
) -> Dict:
    """
    Returns a dict with the question AND the evidence behind it:

        {
          "question": "...",
          "topic": "the skill/domain this question targets",
          "sources": [{"source": "book.pdf", "distance": 0.31}, ...],
          "done": False
        }

    `sources` is what gives us traceability -- we always know which
    textbook chunks influenced any given question.

    `previous_answer`, when provided, lets the question adapt: a thin
    answer nudges the next question to be more foundational; a strong
    answer nudges it to go deeper. This is what the assignment calls
    "questions may adapt based on previous responses."

    Alternates between a personalized style (ties the question to the
    candidate's specific projects) and a general style (tests the concept
    on its own merits) -- a real interview mixes both. The topic itself is
    always chosen based on resume + KB coverage either way; only whether
    the QUESTION TEXT names the candidate's project changes.
    """
    asked_topics = asked_topics or []
    topic, retrieved_chunks = select_best_topic(resume_data, role, asked_topics)

    if topic is None:
        return {"question": None, "topic": None, "sources": [], "done": True}

    context_text = "\n\n".join(chunk["text"] for chunk in retrieved_chunks)

    adaptive_note = ""
    if previous_answer:
        adaptive_note = ADAPTIVE_NOTE_TEMPLATE.format(previous_answer=previous_answer)

    # Even-numbered questions (0th, 2nd, 4th...) are personalized;
    # odd-numbered ones are general. First question is always personalized
    # so the interview opens by acknowledging the candidate's background.
    question_index = len(asked_topics)
    use_personalized = question_index % 2 == 0

    if use_personalized:
        prompt = PERSONALIZED_PROMPT.format(
            role=role,
            skills=", ".join(resume_data.get("skills", [])) or "not specified",
            technologies=", ".join(resume_data.get("technologies", [])) or "not specified",
            projects="; ".join(resume_data.get("notable_projects", [])) or "not specified",
            topic=topic,
            context=context_text,
            adaptive_note=adaptive_note,
        )
    else:
        prompt = GENERAL_PROMPT.format(role=role, topic=topic, context=context_text, adaptive_note=adaptive_note)

    question_text = generate(prompt, max_output_tokens=1024).strip()

    # Safety net: if the response looks cut off mid-sentence (no ending
    # punctuation), it likely hit the token cap before finishing -- retry
    # once with a bigger cap rather than ever showing a broken question.
    if _looks_truncated(question_text):
        question_text = generate(prompt, max_output_tokens=2048).strip()

    return {
        "question": question_text,
        "topic": topic,
        "sources": [{"source": c["source"], "distance": round(c["distance"], 4)} for c in retrieved_chunks],
        "done": False,
    }


if __name__ == "__main__":
    import json
    import sys

    from app.services.resume_parser import parse_resume

    resume_path = sys.argv[1] if len(sys.argv) > 1 else "data/knowledge_base/my_resume.pdf"
    role = sys.argv[2] if len(sys.argv) > 2 else "ai_ml_engineer"

    print("Parsing resume...")
    resume_data = parse_resume(resume_path)

    print("\nGenerating first question...\n")
    result = generate_question(resume_data, role)
    print(f"Topic probed: {result['topic']}")
    print(f"Question: {result['question']}")
    print(f"Sources: {json.dumps(result['sources'], indent=2)}")
