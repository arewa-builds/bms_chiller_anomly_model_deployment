"""ChromaDB client factory — embedded, server, or Chroma Cloud."""

from __future__ import annotations

import chromadb
from chromadb.api import ClientAPI

from copilot.config import (
    CHROMA_API_KEY,
    CHROMA_COLLECTION_NAME,
    CHROMA_DATABASE,
    CHROMA_HOST,
    CHROMA_MODE,
    CHROMA_PERSIST_DIR,
    CHROMA_PORT,
    CHROMA_TENANT,
)


def _require_cloud_credentials() -> None:
    missing = [
        name
        for name, value in [
            ("CHROMA_API_KEY", CHROMA_API_KEY),
            ("CHROMA_TENANT", CHROMA_TENANT),
            ("CHROMA_DATABASE", CHROMA_DATABASE),
        ]
        if not value
    ]
    if missing:
        raise ValueError(
            f"Chroma Cloud requires: {', '.join(missing)}. "
            "Copy .env.copilot.example → .env.copilot and fill in values "
            "from your Chroma dashboard (BMS → Connect)."
        )


def get_chroma_client() -> ClientAPI:
    """
    Return a Chroma client.

    Modes (set CHROMA_MODE env var):
      - embedded  → local files in ./chroma_db/
      - server    → local Chroma HTTP server
      - cloud     → Chroma Cloud (database: BMS)
    """
    if CHROMA_MODE == "cloud":
        _require_cloud_credentials()
        return chromadb.CloudClient(
            api_key=CHROMA_API_KEY,
            tenant=CHROMA_TENANT,
            database=CHROMA_DATABASE,
        )

    if CHROMA_MODE == "server":
        return chromadb.HttpClient(host=CHROMA_HOST, port=CHROMA_PORT)

    return chromadb.PersistentClient(path=CHROMA_PERSIST_DIR)


def get_langchain_cloud_kwargs() -> dict:
    """Extra kwargs for langchain_chroma.Chroma when using Chroma Cloud."""
    if CHROMA_MODE != "cloud":
        return {}
    _require_cloud_credentials()
    return {
        "chroma_cloud_api_key": CHROMA_API_KEY,
        "tenant": CHROMA_TENANT,
        "database": CHROMA_DATABASE,
    }


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
    if CHROMA_MODE == "cloud":
        tenant_label = CHROMA_TENANT[:12] + "..." if len(CHROMA_TENANT) > 12 else CHROMA_TENANT or "(not set)"
        return f"cloud @ database={CHROMA_DATABASE}, tenant={tenant_label}"
    if CHROMA_MODE == "server":
        return f"server @ {CHROMA_HOST}:{CHROMA_PORT}"
    return f"embedded @ {CHROMA_PERSIST_DIR}"
