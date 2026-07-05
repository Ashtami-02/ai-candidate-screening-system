# AI-Powered Candidate Screening System

A RAG-based technical interview simulator. Upload a resume, pick a role, and get a live, personalized technical interview grounded in a role-specific knowledge base.

## How it works

1. Candidate uploads a resume (PDF/.txt) and selects a target role
2. An LLM extracts skills, technologies, domains, and projects from the resume
3. For each question, the system picks a resume topic, retrieves relevant chunks from a vector knowledge base built from role-specific textbooks, and generates a grounded interview question
4. Candidate answers through the React UI; the next question adapts based on the previous answer
5. After 5 questions, a summary is generated with an LLM-written analysis of the session

**Pipeline:**
```
Resume + Role → Resume Parsing (LLM) → Topic Selection → Retrieval (ChromaDB)
             → Question Generation (LLM) → Candidate Answer → repeat x5
             → Session Insights (LLM) → Summary
```

## Tech stack

- **Backend**: FastAPI + SQLAlchemy + SQLite
- **RAG**: ChromaDB (vector store) + `sentence-transformers` (local embeddings)
- **LLM**: Gemini 2.5 Flash-Lite
- **Frontend**: React (Vite)
- **Resume parsing**: `pypdf` + Gemini

## Setup

### Backend

```bash
cd backend
python -m venv venv
venv\Scripts\activate        # Windows
# source venv/bin/activate   # Mac/Linux
pip install -r requirements.txt
cp .env.example .env
```

Edit `.env` and add your Gemini API key (get one free at [aistudio.google.com/app/apikey](https://aistudio.google.com/app/apikey)):
```
GEMINI_API_KEY=your_key_here
GEMINI_MODEL=gemini-2.5-flash-lite
```

Build the knowledge base (one-time):
```bash
python scripts/build_kb.py --pdf data/knowledge_base/your_book.pdf --role ai_ml_engineer
```

Run the backend:
```bash
uvicorn app.main:app --reload
```

API docs available at `http://127.0.0.1:8000/docs`.

### Frontend

```bash
cd frontend
npm install
npm run dev
```

Open the printed local URL (typically `http://localhost:5173`). Backend must be running at the same time.

## API endpoints

- `POST /interview/sessions` — start a session (resume + role) → first question
- `POST /interview/sessions/{id}/answer` — submit an answer → next question
- `GET /interview/sessions/{id}/summary` — full Q&A history + insights
