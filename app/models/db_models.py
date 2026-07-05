"""
Two tables:

InterviewSession -- one row per candidate interview (which resume, which
role, when it started).

QuestionAnswer -- one row per question asked in a session, including the
answer once given. Storing `sources_json` (which textbook chunks fed this
question) is what gives us traceability per-question, not just in memory
during generation.
"""

import datetime
import json

from sqlalchemy import Column, Integer, String, Text, DateTime, ForeignKey
from sqlalchemy.orm import relationship

from app.db.database import Base


class InterviewSession(Base):
    __tablename__ = "interview_sessions"

    id = Column(Integer, primary_key=True, index=True)
    role = Column(String, nullable=False)
    resume_filename = Column(String, nullable=False)
    # Parsed resume (skills/technologies/domains/etc.) stored as a JSON
    # string -- SQLite has no native JSON column type, so this is the
    # simplest portable way to persist a structured dict.
    resume_data_json = Column(Text, nullable=False)
    created_at = Column(DateTime, default=datetime.datetime.utcnow)

    qa_pairs = relationship(
        "QuestionAnswer", back_populates="session", cascade="all, delete-orphan"
    )

    def get_resume_data(self) -> dict:
        return json.loads(self.resume_data_json)


class QuestionAnswer(Base):
    __tablename__ = "question_answers"

    id = Column(Integer, primary_key=True, index=True)
    session_id = Column(Integer, ForeignKey("interview_sessions.id"), nullable=False)
    topic = Column(String, nullable=True)
    question_text = Column(Text, nullable=False)
    sources_json = Column(Text, nullable=True)
    answer_text = Column(Text, nullable=True)
    asked_at = Column(DateTime, default=datetime.datetime.utcnow)
    answered_at = Column(DateTime, nullable=True)

    session = relationship("InterviewSession", back_populates="qa_pairs")
