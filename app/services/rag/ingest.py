"""
Knowledge ingestion pipeline.

Flow: PDF file -> raw text -> overlapping chunks -> embeddings -> ChromaDB

This module is imported by scripts/build_kb.py (to run once per book) and
later by retrieve.py (to query what we stored here).
"""

import os
from pathlib import Path
from typing import List

os.environ["ANONYMIZED_TELEMETRY"] = "False"

import chromadb
from pypdf import PdfReader
from sentence_transformers import SentenceTransformer

from app.config import settings

# Loaded once and reused across calls -- loading this model takes a few
# seconds, so we don't want to reload it for every single chunk.
_embedding_model = None


def get_embedding_model() -> SentenceTransformer:
    global _embedding_model
    if _embedding_model is None:
        # all-MiniLM-L6-v2: small (~80MB), fast, runs on CPU, good enough
        # quality for this use case. Downloads once, then cached locally.
        _embedding_model = SentenceTransformer("all-MiniLM-L6-v2")
    return _embedding_model


def extract_text_from_pdf(pdf_path: str) -> str:
    """Pull raw text out of every page of the PDF and join it together."""
    reader = PdfReader(pdf_path)
    full_text = []
    for page in reader.pages:
        text = page.extract_text()
        if text:
            full_text.append(text)
    return "\n".join(full_text)


def chunk_text(text: str, chunk_size: int = 1000, overlap: int = 150) -> List[str]:
    """
    Split text into overlapping chunks, measured in characters.

    chunk_size=1000 chars is roughly 150-200 words -- small enough to be a
    focused, specific piece of context, big enough to contain a full idea.
    overlap=150 chars means each chunk repeats the tail of the previous one,
    so a sentence that falls near a chunk boundary still appears in full
    inside at least one chunk.
    """
    chunks = []
    start = 0
    text_length = len(text)

    while start < text_length:
        end = start + chunk_size
        chunk = text[start:end].strip()
        if chunk:  # skip empty chunks (can happen at the very end)
            chunks.append(chunk)
        # Move forward by (chunk_size - overlap), not by chunk_size --
        # this is what creates the overlap between consecutive chunks.
        start += chunk_size - overlap

    return chunks


def build_knowledge_base(pdf_path: str, role: str) -> int:
    """
    Full pipeline for one book: extract -> chunk -> embed -> store.

    `role` becomes the ChromaDB collection name (e.g. "ai_ml_engineer"),
    so different roles can have separate, non-overlapping knowledge bases --
    this matters because the assignment calls for a *role-specific*
    knowledge base, not one shared blob for every role.

    Returns the number of chunks stored (useful to sanity-check the run).
    """
    print(f"Extracting text from {pdf_path} ...")
    text = extract_text_from_pdf(pdf_path)
    print(f"Extracted {len(text)} characters")

    print("Chunking text ...")
    chunks = chunk_text(text)
    print(f"Created {len(chunks)} chunks")

    print("Loading embedding model (first run downloads it, ~80MB) ...")
    model = get_embedding_model()

    print("Generating embeddings for all chunks ...")
    embeddings = model.encode(chunks, show_progress_bar=True).tolist()

    print(f"Storing in ChromaDB under collection '{role}' ...")
    client = chromadb.PersistentClient(path=settings.chroma_persist_dir)
    collection = client.get_or_create_collection(name=role)

    # Chroma needs a unique string id per item. We include the source
    # filename (not just role) so that adding a SECOND pdf under the same
    # role doesn't collide with ids from the first one -- without this,
    # re-running build_kb.py for a new book under an existing role would
    # crash with a duplicate-id error instead of appending new chunks.
    source_name = Path(pdf_path).stem
    ids = [f"{role}_{source_name}_chunk_{i}" for i in range(len(chunks))]
    metadatas = [{"source": Path(pdf_path).name, "chunk_index": i} for i in range(len(chunks))]

    collection.add(
        ids=ids,
        embeddings=embeddings,
        documents=chunks,
        metadatas=metadatas,
    )

    print(f"Done. {len(chunks)} chunks added from this file.")
    print(f"Collection '{role}' now contains {collection.count()} chunks total.")
    return len(chunks)
