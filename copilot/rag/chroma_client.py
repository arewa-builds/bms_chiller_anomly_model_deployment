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

# Values from .env.copilot.example — fail fast instead of a 401 from Chroma Cloud
_PLACEHOLDER_MARKERS = (
    "your-api-key",
    "your-tenant",
    "ck-your-api-key",
    "changeme",
    "replace-me",
    "<",
    ">",
)


def _looks_like_placeholder(value: str) -> bool:
    lowered = value.strip().lower()
    if not lowered:
        return True
    return any(marker in lowered for marker in _PLACEHOLDER_MARKERS)


def _require_cloud_credentials() -> None:
    problems: list[str] = []

    if not CHROMA_API_KEY or _looks_like_placeholder(CHROMA_API_KEY):
        problems.append(
            "CHROMA_API_KEY is missing or still a placeholder. "
            "Copy .env.copilot.example → .env.copilot and paste your key from "
            "Chroma dashboard → BMS → Connect (starts with ck-)."
        )
    elif not CHROMA_API_KEY.startswith("ck-"):
        problems.append(
            "CHROMA_API_KEY does not look valid (expected to start with ck-)."
        )

    if not CHROMA_TENANT or _looks_like_placeholder(CHROMA_TENANT):
        problems.append(
            "CHROMA_TENANT is missing or still a placeholder. "
            "Use the tenant UUID from the Chroma dashboard Connect panel."
        )

    if not CHROMA_DATABASE or _looks_like_placeholder(CHROMA_DATABASE):
        problems.append(
            "CHROMA_DATABASE is missing or still a placeholder (expected: BMS)."
        )

    if problems:
        raise ValueError(
            "Chroma Cloud is not configured:\n"
            + "\n".join(f"  - {item}" for item in problems)
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
        tenant_label = (
            CHROMA_TENANT[:12] + "..."
            if len(CHROMA_TENANT) > 12
            else CHROMA_TENANT or "(not set)"
        )
        return f"cloud @ database={CHROMA_DATABASE}, tenant={tenant_label}"
    if CHROMA_MODE == "server":
        return f"server @ {CHROMA_HOST}:{CHROMA_PORT}"
    return f"embedded @ {CHROMA_PERSIST_DIR}"
