"""
Session orchestration layer.

This module is intentionally the ONLY place that knows how to combine:
resume parsing + RAG question generation + database persistence.
Routers (interview.py) stay thin -- they just call these functions and
translate results to/from HTTP. This separation is what the assignment
means by "clear separation of responsibilities": if you ever swap the
web framework, or add a CLI, or add tests, this logic doesn't change.
"""

import datetime
import json

from sqlalchemy.orm import Session

from app.models.db_models import InterviewSession, QuestionAnswer
from app.services.resume_parser import parse_resume
from app.services.rag.generate import generate_question, generate_session_insights

# Caps the interview length so a session naturally reaches "done" instead
# of asking forever -- also protects your Gemini free-tier quota during
# testing and demoing.
MAX_QUESTIONS = 5


def create_session(db: Session, resume_path: str, role: str) -> dict:
    resume_data = parse_resume(resume_path)

    session = InterviewSession(
        role=role,
        resume_filename=resume_path.split("/")[-1].split("\\")[-1],
        resume_data_json=json.dumps(resume_data),
    )
    db.add(session)
    db.commit()
    db.refresh(session)

    first_question = _create_next_question(db, session)
    return {"session_id": session.id, "role": role, "first_question": first_question}


def _create_next_question(db: Session, session: InterviewSession) -> dict:
    resume_data = session.get_resume_data()
    asked_topics = [qa.topic for qa in session.qa_pairs if qa.topic]

    if len(session.qa_pairs) >= MAX_QUESTIONS:
        return {"question_id": None, "question": None, "topic": None, "done": True}

    # Find the most recently answered question, if any, so the next
    # question can calibrate its difficulty to how strong that answer was.
    answered = [qa for qa in session.qa_pairs if qa.answer_text]
    previous_answer = answered[-1].answer_text if answered else None

    result = generate_question(resume_data, session.role, asked_topics, previous_answer)

    if result["done"]:
        return {"question_id": None, "question": None, "topic": None, "done": True}

    qa = QuestionAnswer(
        session_id=session.id,
        topic=result["topic"],
        question_text=result["question"],
        sources_json=json.dumps(result["sources"]),
    )
    db.add(qa)
    db.commit()
    db.refresh(qa)

    return {"question_id": qa.id, "question": qa.question_text, "topic": qa.topic, "done": False}


def submit_answer(db: Session, session_id: int, question_id: int, answer_text: str) -> dict:
    session = db.query(InterviewSession).filter(InterviewSession.id == session_id).first()
    if session is None:
        raise ValueError("Session not found")

    qa = (
        db.query(QuestionAnswer)
        .filter(QuestionAnswer.id == question_id, QuestionAnswer.session_id == session_id)
        .first()
    )
    if qa is None:
        raise ValueError("Question not found for this session")

    qa.answer_text = answer_text
    qa.answered_at = datetime.datetime.utcnow()
    db.commit()

    return _create_next_question(db, session)


def get_summary(db: Session, session_id: int) -> dict:
    session = db.query(InterviewSession).filter(InterviewSession.id == session_id).first()
    if session is None:
        raise ValueError("Session not found")

    qa_pairs = [
        {"topic": qa.topic, "question": qa.question_text, "answer": qa.answer_text}
        for qa in session.qa_pairs
    ]
    answered = sum(1 for qa in session.qa_pairs if qa.answer_text)

    try:
        insights = generate_session_insights(qa_pairs, session.role)
    except Exception as e:
        # The interview data itself is already safely in the database --
        # an LLM failure on this LAST, optional analysis step should never
        # block the candidate from seeing their own completed summary.
        insights = f"Analysis unavailable right now ({e}). Your questions and answers are saved above."

    return {
        "session_id": session.id,
        "role": session.role,
        "total_questions": len(session.qa_pairs),
        "answered_questions": answered,
        "qa_pairs": qa_pairs,
        "insights": insights,
    }
