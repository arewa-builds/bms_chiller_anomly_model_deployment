"""Copilot configuration — Step 1: ingestion and retrieval only."""

import os
from pathlib import Path

# Repository root (parent of copilot/)
REPO_ROOT = Path(__file__).resolve().parent.parent

# Document sources
DOCUMENTS_DIR = REPO_ROOT / "data" / "documents"

# ChromaDB
CHROMA_PERSIST_DIR = os.getenv("CHROMA_PERSIST_DIR", str(REPO_ROOT / "chroma_db"))
CHROMA_COLLECTION_NAME = os.getenv("CHROMA_COLLECTION_NAME", "chiller_troubleshooting")

# Chunking defaults (tune via evaluation in later steps)
CHUNK_SIZE = int(os.getenv("CHUNK_SIZE", "1000"))
CHUNK_OVERLAP = int(os.getenv("CHUNK_OVERLAP", "150"))

# Retrieval defaults
RETRIEVAL_TOP_K = int(os.getenv("RETRIEVAL_TOP_K", "4"))

# Local embedding model (no API key required for Step 1)
EMBEDDING_MODEL = os.getenv(
    "EMBEDDING_MODEL",
    "sentence-transformers/all-MiniLM-L6-v2",
)
