"""Embedding model factory — local (ingest) or OpenAI (API runtime)."""

from __future__ import annotations

from langchain_core.embeddings import Embeddings

from copilot.config import (
    EMBEDDING_BACKEND,
    EMBEDDING_MODEL,
    OPENAI_API_KEY,
    OPENAI_EMBEDDING_MODEL,
)


def get_embeddings() -> Embeddings:
    """
    Return the configured embedding model.

    ``local`` — HuggingFace sentence-transformers (requires torch; use for ingest).
    ``openai`` — OpenAI API embeddings (thin runtime; use for Docker API).
    """
    backend = EMBEDDING_BACKEND.lower().strip()
    if backend == "openai":
        if not OPENAI_API_KEY or OPENAI_API_KEY.startswith("sk-your"):
            raise ValueError(
                "EMBEDDING_BACKEND=openai requires OPENAI_API_KEY in .env.copilot"
            )
        from langchain_openai import OpenAIEmbeddings

        return OpenAIEmbeddings(model=OPENAI_EMBEDDING_MODEL)

    if backend == "local":
        from langchain_huggingface import HuggingFaceEmbeddings

        return HuggingFaceEmbeddings(model_name=EMBEDDING_MODEL)

    raise ValueError(
        f"Unknown EMBEDDING_BACKEND '{EMBEDDING_BACKEND}'. Use 'local' or 'openai'."
    )
