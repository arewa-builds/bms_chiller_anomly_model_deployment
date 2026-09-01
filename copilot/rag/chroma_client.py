"""ChromaDB client factory — embedded (local files) or server (HTTP)."""

from __future__ import annotations

import chromadb
from chromadb.api import ClientAPI

from copilot.config import (
    CHROMA_COLLECTION_NAME,
    CHROMA_HOST,
    CHROMA_MODE,
    CHROMA_PERSIST_DIR,
    CHROMA_PORT,
)


def get_chroma_client() -> ClientAPI:
    """
    Return a Chroma client.

    Modes (set CHROMA_MODE env var):
      - embedded  → local files in ./chroma_db/  (default)
      - server    → Chroma HTTP server (docker compose chroma service)
    """
    if CHROMA_MODE == "server":
        return chromadb.HttpClient(host=CHROMA_HOST, port=CHROMA_PORT)

    return chromadb.PersistentClient(path=CHROMA_PERSIST_DIR)


def get_collection(create: bool = False):
    """Return the chiller_troubleshooting collection."""
    client = get_chroma_client()
    if create:
        return client.get_or_create_collection(name=CHROMA_COLLECTION_NAME)
    return client.get_collection(name=CHROMA_COLLECTION_NAME)


def delete_collection_if_exists() -> None:
    """Delete the collection (used before re-ingest)."""
    client = get_chroma_client()
    try:
        client.delete_collection(name=CHROMA_COLLECTION_NAME)
    except Exception:
        pass


def connection_info() -> str:
    """Human-readable connection string for logging."""
    if CHROMA_MODE == "server":
        return f"server @ {CHROMA_HOST}:{CHROMA_PORT}"
    return f"embedded @ {CHROMA_PERSIST_DIR}"
