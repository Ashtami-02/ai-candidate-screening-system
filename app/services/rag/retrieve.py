"""
Retrieval: given a query and a role, return the most relevant chunks
from that role's knowledge base.

This is literally the "R" in RAG. Everything before this (ingest.py)
was one-time setup; this module runs on every single question we
generate later.
"""

import os
from typing import List, Dict

os.environ["ANONYMIZED_TELEMETRY"] = "False"

import chromadb

from app.config import settings
from app.services.rag.ingest import get_embedding_model

# Cached across calls -- select_best_topic() in generate.py calls this
# function once per candidate topic, and recreating a database connection
# every time would be wasteful (and was the real cause of the repeated
# telemetry noise you saw -- each new client tried to fire a startup event).
_client = None
_collections = {}


def _get_client():
    global _client
    if _client is None:
        _client = chromadb.PersistentClient(path=settings.chroma_persist_dir)
    return _client


def _get_collection(role: str):
    if role not in _collections:
        _collections[role] = _get_client().get_or_create_collection(name=role)
    return _collections[role]


def retrieve_relevant_chunks_batch(queries: List[str], role: str, top_k: int = 3) -> List[List[Dict]]:
    """
    Same as retrieve_relevant_chunks, but for MANY queries at once.

    Why this exists: checking N candidate topics one at a time means N
    separate embedding calls and N separate database round trips. Batching
    embeds all N queries in a single forward pass (much faster on CPU due
    to batching) and sends ChromaDB one query call instead of N -- this is
    what actually fixes the slow "start interview" / "next question" lag
    when a resume has many skills.

    Returns a list of chunk-lists, in the same order as `queries`.
    """
    model = get_embedding_model()
    query_embeddings = model.encode(queries).tolist()

    collection = _get_collection(role)
    results = collection.query(
        query_embeddings=query_embeddings,
        n_results=top_k,
        include=["documents", "distances", "metadatas"],
    )

    all_results = []
    for docs, dists, metas in zip(results["documents"], results["distances"], results["metadatas"]):
        chunks = [
            {"text": d, "distance": dist, "source": meta.get("source")}
            for d, dist, meta in zip(docs, dists, metas)
        ]
        all_results.append(chunks)
    return all_results


def retrieve_relevant_chunks(query: str, role: str, top_k: int = 3) -> List[Dict]:
    """
    Args:
        query: natural language text to search for, e.g.
               "candidate has experience with scikit-learn and pandas"
        role: which knowledge base to search (must match a role name
              used when you ran build_kb.py)
        top_k: how many chunks to return. 3-5 is a good range -- too few
               and you might miss relevant context, too many and you
               dilute the prompt with less-relevant material and waste
               tokens.

    Returns:
        A list of dicts, each with 'text' (the chunk) and 'distance'
        (how close it is to the query -- lower means more similar).
    """
    model = get_embedding_model()
    query_embedding = model.encode([query]).tolist()

    collection = _get_collection(role)

    results = collection.query(
        query_embeddings=query_embedding,
        n_results=top_k,
        include=["documents", "distances", "metadatas"],
    )

    # Chroma returns parallel lists (documents[0], distances[0], etc.)
    # for the single query we sent. We zip them into a cleaner structure.
    # Including metadata (source filename) is what gives us traceability --
    # later, when we generate a question, we can point back to exactly
    # which document and chunk it came from.
    chunks = []
    for doc, distance, metadata in zip(
        results["documents"][0], results["distances"][0], results["metadatas"][0]
    ):
        chunks.append({"text": doc, "distance": distance, "source": metadata.get("source")})

    return chunks


if __name__ == "__main__":
    # Quick manual test: run this file directly to sanity-check retrieval
    # before we wire it into anything else.
    #   python -m app.services.rag.retrieve
    import sys

    test_query = sys.argv[1] if len(sys.argv) > 1 else "overfitting in decision trees"
    test_role = sys.argv[2] if len(sys.argv) > 2 else "ai_ml_engineer"

    print(f"Query: '{test_query}'  |  Role: '{test_role}'\n")
    results = retrieve_relevant_chunks(test_query, test_role)

    for i, chunk in enumerate(results, 1):
        print(f"--- Result {i} | source: {chunk['source']} | distance: {chunk['distance']:.4f} ---")
        print(chunk["text"][:300], "...\n")
