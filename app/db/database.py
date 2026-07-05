"""
SQLAlchemy engine + session setup.

`get_db` is a FastAPI dependency: FastAPI calls it before each request that
needs one, hands the route a database session, then closes it automatically
afterward -- even if the route raises an error. This is the standard
FastAPI + SQLAlchemy pattern; you'll see it in almost every real project
using this stack.
"""

from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker, declarative_base

from app.config import settings

engine = create_engine(
    settings.database_url,
    connect_args={"check_same_thread": False} if "sqlite" in settings.database_url else {},
)
SessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=engine)
Base = declarative_base()


def get_db():
    db = SessionLocal()
    try:
        yield db
    finally:
        db.close()
