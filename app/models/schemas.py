"""
Pydantic schemas -- these define exactly what shape of JSON the API
accepts and returns. FastAPI uses these to auto-generate the /docs page
and to validate incoming requests automatically (e.g. reject a request
missing `answer_text` before it ever reaches your business logic).
"""

from typing import List, Optional
from pydantic import BaseModel


class QuestionOut(BaseModel):
    question_id: Optional[int]
    question: Optional[str]
    topic: Optional[str]
    done: bool = False


class SessionCreateOut(BaseModel):
    session_id: int
    role: str
    first_question: QuestionOut


class AnswerIn(BaseModel):
    question_id: int
    answer_text: str


class SummaryQA(BaseModel):
    topic: Optional[str]
    question: str
    answer: Optional[str]


class SummaryOut(BaseModel):
    session_id: int
    role: str
    total_questions: int
    answered_questions: int
    qa_pairs: List[SummaryQA]
    insights: str
