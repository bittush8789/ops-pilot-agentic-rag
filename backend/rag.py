"""
rag.py — Pinecone RAG pipeline for operational runbooks.

Responsibilities:
  - Load and chunk markdown runbook documents
  - Generate embeddings using sentence-transformers (local, no extra API key)
  - Upsert vectors into Pinecone
  - Provide search_runbook() for agent tool use
"""
from __future__ import annotations

import hashlib
import os
import sys
import time
from pathlib import Path
from typing import Optional

# Ensure project root is in sys.path when executed directly as a script
_project_root = str(Path(__file__).resolve().parent.parent)
if _project_root not in sys.path:
    sys.path.insert(0, _project_root)

import structlog

from backend.config import settings

log = structlog.get_logger(__name__)

# ── Lazy imports to avoid startup errors if dependencies missing ──

def _get_embedding_model():
    """Lazily load sentence-transformers model."""
    from sentence_transformers import SentenceTransformer
    return SentenceTransformer(settings.embedding_model)


def _get_pinecone_index():
    """Return a Pinecone index client."""
    from pinecone import Pinecone
    pc = Pinecone(api_key=settings.pinecone_api_key)
    return pc.Index(settings.pinecone_index_name)


# ── Document loading and chunking ─────────────────────────────────

RUNBOOK_DIR = Path(__file__).parent.parent / "data" / "runbooks"
CHUNK_SIZE = 800          # characters per chunk
CHUNK_OVERLAP = 100       # overlap between chunks


def _load_markdown_files(directory: Path) -> list[dict]:
    """Load all .md files from directory, return list of {source, content} dicts."""
    documents = []
    for md_file in sorted(directory.glob("*.md")):
        content = md_file.read_text(encoding="utf-8")
        documents.append({
            "source": md_file.stem,
            "filename": md_file.name,
            "content": content,
        })
        log.info("Loaded runbook", file=md_file.name, chars=len(content))
    return documents


def _chunk_document(doc: dict) -> list[dict]:
    """Split document content into overlapping chunks."""
    content = doc["content"]
    chunks = []
    start = 0
    chunk_index = 0

    while start < len(content):
        end = start + CHUNK_SIZE
        chunk_text = content[start:end]

        # Try to break at a paragraph boundary
        if end < len(content):
            last_newline = chunk_text.rfind("\n\n")
            if last_newline > CHUNK_SIZE // 2:
                end = start + last_newline
                chunk_text = content[start:end]

        # Generate stable ID from content hash
        chunk_id = hashlib.md5(
            f"{doc['source']}::{chunk_index}".encode()
        ).hexdigest()

        chunks.append({
            "id": chunk_id,
            "source": doc["source"],
            "filename": doc["filename"],
            "chunk_index": chunk_index,
            "text": chunk_text.strip(),
        })

        start = end - CHUNK_OVERLAP
        chunk_index += 1

    return chunks


def _prepare_all_chunks() -> list[dict]:
    """Load and chunk all runbook documents."""
    documents = _load_markdown_files(RUNBOOK_DIR)
    all_chunks = []
    for doc in documents:
        chunks = _chunk_document(doc)
        all_chunks.extend(chunks)
        log.info("Chunked document", source=doc["source"], chunks=len(chunks))
    return all_chunks


# ── Pinecone ingestion ────────────────────────────────────────────

def ingest_runbooks(batch_size: int = 50) -> dict:
    """
    Load runbooks, generate embeddings, upsert into Pinecone.
    Returns summary of ingestion.
    """
    log.info("Starting runbook ingestion")

    if not settings.pinecone_api_key:
        log.warning("PINECONE_API_KEY not set — skipping ingestion")
        return {"status": "skipped", "reason": "PINECONE_API_KEY not configured"}

    model = _get_embedding_model()
    index = _get_pinecone_index()

    chunks = _prepare_all_chunks()
    log.info("Prepared chunks", total=len(chunks))

    upserted = 0
    for i in range(0, len(chunks), batch_size):
        batch = chunks[i : i + batch_size]
        texts = [c["text"] for c in batch]

        # Generate embeddings
        embeddings = model.encode(texts, show_progress_bar=False).tolist()

        # Prepare vectors for Pinecone
        vectors = []
        for chunk, embedding in zip(batch, embeddings):
            vectors.append({
                "id": chunk["id"],
                "values": embedding,
                "metadata": {
                    "source": chunk["source"],
                    "filename": chunk["filename"],
                    "chunk_index": chunk["chunk_index"],
                    "text": chunk["text"][:1000],  # Pinecone metadata limit
                },
            })

        index.upsert(vectors=vectors)
        upserted += len(vectors)
        log.info("Upserted batch", batch=i // batch_size + 1, count=len(vectors))

        # Small delay to avoid rate limiting
        time.sleep(0.1)

    log.info("Ingestion complete", total_upserted=upserted)
    return {
        "status": "success",
        "documents": len(_load_markdown_files(RUNBOOK_DIR)),
        "chunks": len(chunks),
        "upserted": upserted,
    }


# ── RAG retrieval ─────────────────────────────────────────────────

def search_runbook(query: str, top_k: int = 4) -> list[dict]:
    """
    Search the Pinecone runbook index for relevant documentation.

    Args:
        query: Natural language query about an operational issue
        top_k: Number of results to return

    Returns:
        List of {source, text, score} dicts ordered by relevance
    """
    if not settings.pinecone_api_key:
        log.warning("PINECONE_API_KEY not set — returning mock runbook context")
        return _mock_runbook_results(query)

    try:
        model = _get_embedding_model()
        index = _get_pinecone_index()

        # Generate query embedding
        query_embedding = model.encode([query])[0].tolist()

        # Query Pinecone
        results = index.query(
            vector=query_embedding,
            top_k=top_k,
            include_metadata=True,
        )

        # Format results
        runbook_chunks = []
        for match in results.get("matches", []):
            metadata = match.get("metadata", {})
            runbook_chunks.append({
                "source": metadata.get("source", "unknown"),
                "filename": metadata.get("filename", "unknown.md"),
                "text": metadata.get("text", ""),
                "score": round(match.get("score", 0.0), 4),
            })

        log.info(
            "Runbook search completed",
            query=query[:50],
            results=len(runbook_chunks),
        )
        return runbook_chunks

    except Exception as e:
        log.error("Runbook search failed", error=str(e))
        return _mock_runbook_results(query)


def _mock_runbook_results(query: str) -> list[dict]:
    """
    Return mock runbook content when Pinecone is unavailable.
    Useful for local development and testing.
    """
    query_lower = query.lower()

    # Return most relevant runbook based on keyword matching
    if any(kw in query_lower for kw in ["timeout", "gateway", "stripe"]):
        source = "payment_gateway_timeout"
    elif any(kw in query_lower for kw in ["duplicate", "double charge"]):
        source = "duplicate_payment"
    elif any(kw in query_lower for kw in ["refund", "chargeback"]):
        source = "failed_refund"
    elif any(kw in query_lower for kw in ["account", "locked", "suspended"]):
        source = "account_lock"
    elif any(kw in query_lower for kw in ["escalat", "incident"]):
        source = "incident_escalation"
    else:
        source = "payment_failure"

    runbook_path = RUNBOOK_DIR / f"{source}.md"
    if runbook_path.exists():
        content = runbook_path.read_text(encoding="utf-8")
        return [{
            "source": source,
            "filename": f"{source}.md",
            "text": content[:2000],
            "score": 0.95,
        }]

    return [{
        "source": "payment_failure",
        "filename": "payment_failure.md",
        "text": "General payment failure runbook — investigate transaction records, check system events, determine scope.",
        "score": 0.70,
    }]


# ── CLI entry point ───────────────────────────────────────────────

if __name__ == "__main__":
    import sys
    import json

    if "--ingest" in sys.argv:
        print("Starting runbook ingestion into Pinecone...")
        result = ingest_runbooks()
        print(json.dumps(result, indent=2))
    elif "--search" in sys.argv:
        idx = sys.argv.index("--search")
        query = sys.argv[idx + 1] if idx + 1 < len(sys.argv) else "payment gateway timeout"
        print(f"Searching for: {query}")
        results = search_runbook(query)
        for r in results:
            print(f"\n[{r['source']}] score={r['score']}")
            print(r["text"][:500])
    else:
        print("Usage: python backend/rag.py --ingest | --search 'query'")
