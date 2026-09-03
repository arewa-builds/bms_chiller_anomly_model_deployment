"""Copilot configuration — Step 1: ingestion and retrieval only."""

import os
from pathlib import Path

# Repository root (parent of copilot/)
REPO_ROOT = Path(__file__).resolve().parent.parent

# Document sources
DOCUMENTS_DIR = REPO_ROOT / "data" / "documents"

# ChromaDB
# Mode: embedded | server | cloud
#   embedded → local files in ./chroma_db/  (default)
#   server   → local Chroma HTTP service (docker compose)
#   cloud    → Chroma Cloud (https://www.trychroma.com)
CHROMA_MODE = os.getenv("CHROMA_MODE", "embedded")
CHROMA_HOST = os.getenv("CHROMA_HOST", "localhost")
CHROMA_PORT = int(os.getenv("CHROMA_PORT", "8001"))
CHROMA_PERSIST_DIR = os.getenv("CHROMA_PERSIST_DIR", str(REPO_ROOT / "chroma_db"))
CHROMA_COLLECTION_NAME = os.getenv("CHROMA_COLLECTION_NAME", "chiller_troubleshooting")

# Chroma Cloud (required when CHROMA_MODE=cloud)
# Get these from: Chroma dashboard → BMS database → Connect
CHROMA_API_KEY = os.getenv("CHROMA_API_KEY", "")
CHROMA_TENANT = os.getenv("CHROMA_TENANT", "")
CHROMA_DATABASE = os.getenv("CHROMA_DATABASE", "BMS")

# Chunking defaults (tune via evaluation in later steps)
CHUNK_SIZE = int(os.getenv("CHUNK_SIZE", "1000"))
CHUNK_OVERLAP = int(os.getenv("CHUNK_OVERLAP", "150"))

# Retrieval defaults
RETRIEVAL_TOP_K = int(os.getenv("RETRIEVAL_TOP_K", "4"))

# LLM (Step 2 — required for RAG chain)
OPENAI_API_KEY = os.getenv("OPENAI_API_KEY", "")
OPENAI_MODEL = os.getenv("OPENAI_MODEL", "gpt-4o-mini")

# Embeddings — local (ingest) or openai (thin API runtime)
# Use the same backend for ingest AND retrieval. Re-ingest when switching.
EMBEDDING_BACKEND = os.getenv("EMBEDDING_BACKEND", "local")  # local | openai
EMBEDDING_MODEL = os.getenv(
    "EMBEDDING_MODEL",
    "sentence-transformers/all-MiniLM-L6-v2",
)
OPENAI_EMBEDDING_MODEL = os.getenv("OPENAI_EMBEDDING_MODEL", "text-embedding-3-small")
