"""
HTTP layer for the interview lifecycle. Each route does three things and
nothing more: validate input, call session_service, translate the result
to/from HTTP. All real logic lives in session_service.py -- this keeps
routes easy to read and easy to test independently of FastAPI itself.
"""

import shutil
from pathlib import Path

from fastapi import APIRouter, Depends, UploadFile, File, Form, HTTPException
from sqlalchemy.orm import Session

from app.db.database import get_db
from app.models import schemas
from app.services import session_service

router = APIRouter(prefix="/interview", tags=["interview"])

UPLOAD_DIR = Path("data/uploads")
UPLOAD_DIR.mkdir(parents=True, exist_ok=True)


@router.post("/sessions", response_model=schemas.SessionCreateOut)
async def create_session(
    role: str = Form(...),
    resume: UploadFile = File(...),
    db: Session = Depends(get_db),
):
    """
    Starts a new interview: candidate uploads a resume and picks a role.
    Returns the session id (needed for every subsequent call) and the
    first generated question.
    """
    if not resume.filename.lower().endswith((".pdf", ".txt")):
        raise HTTPException(status_code=400, detail="Resume must be a .pdf or .txt file")

    save_path = UPLOAD_DIR / resume.filename
    with save_path.open("wb") as f:
        shutil.copyfileobj(resume.file, f)

    try:
        result = session_service.create_session(db, str(save_path), role)
    except Exception as e:
        # Broad catch here is intentional: this endpoint touches resume
        # parsing (LLM call) AND the RAG pipeline, both of which can fail
        # for reasons outside our control (quota, malformed PDF, etc).
        # We surface the reason rather than a bare 500 with no context.
        raise HTTPException(status_code=500, detail=f"Failed to create session: {e}")

    return result


@router.post("/sessions/{session_id}/answer", response_model=schemas.QuestionOut)
def answer_question(
    session_id: int,
    payload: schemas.AnswerIn,
    db: Session = Depends(get_db),
):
    """
    Candidate submits an answer to the current question. Returns the
    NEXT question, or done=True if the interview is complete.
    """
    try:
        return session_service.submit_answer(db, session_id, payload.question_id, payload.answer_text)
    except ValueError as e:
        raise HTTPException(status_code=404, detail=str(e))
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Failed to process answer: {e}")


@router.get("/sessions/{session_id}/summary", response_model=schemas.SummaryOut)
def get_summary(session_id: int, db: Session = Depends(get_db)):
    """Final structured summary: every question, every answer, per the brief."""
    try:
        return session_service.get_summary(db, session_id)
    except ValueError as e:
        raise HTTPException(status_code=404, detail=str(e))
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Failed to load summary: {e}")
