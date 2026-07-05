"""
Entry point. Run with: uvicorn app.main:app --reload
Then visit http://127.0.0.1:8000/docs for interactive API docs.
"""

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware

from app.config import settings
from app.db.database import Base, engine
from app.models import db_models  # noqa: F401  -- import registers the models with Base
from app.routers import interview
from app.services.rag.ingest import get_embedding_model

# Creates the actual .db file and tables the first time this runs, if they
# don't already exist. Safe to call every startup -- it won't touch
# existing tables/data.
Base.metadata.create_all(bind=engine)

# Load the embedding model NOW, at server startup, instead of letting it
# lazy-load on whoever's first request happens to be. Without this, the
# very first "Start Interview" click after a server restart pays an extra
# few seconds for model loading on top of the normal Gemini call latency --
# exactly the kind of hidden delay that looks bad in a live demo.
get_embedding_model()

app = FastAPI(title="AI Candidate Screening System")

# Allows the React frontend (running on a different port, e.g. 5173 or
# 3000) to call this API from the browser. Wide open ("*") is fine for
# local development; a real deployment would restrict this to the actual
# frontend domain.
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

app.include_router(interview.router)


@app.get("/health")
def health_check():
    return {
        "status": "ok",
        "gemini_model_configured": settings.gemini_model,
    }
