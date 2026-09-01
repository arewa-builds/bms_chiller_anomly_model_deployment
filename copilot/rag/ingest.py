"""
Step 1 — Document ingestion for ChromaDB.

Loads engineering manuals and SOPs, splits into chunks, embeds them,
and persists to the chiller_troubleshooting collection.
"""

from __future__ import annotations

import re
from pathlib import Path

from langchain_chroma import Chroma
from langchain_community.document_loaders import DirectoryLoader, TextLoader
from langchain_huggingface import HuggingFaceEmbeddings
from langchain_text_splitters import RecursiveCharacterTextSplitter

from copilot.config import (
    CHROMA_COLLECTION_NAME,
    CHUNK_OVERLAP,
    CHUNK_SIZE,
    DOCUMENTS_DIR,
    EMBEDDING_MODEL,
)
from copilot.rag.chroma_client import (
    delete_collection_if_exists,
    get_chroma_client,
    get_langchain_cloud_kwargs,
)


def _parse_frontmatter_metadata(text: str) -> dict:
    """Extract simple key: value metadata from markdown header lines."""
    metadata: dict[str, str] = {}
    for line in text.splitlines()[:20]:
        match = re.match(r"^\*\*(.+?):\*\*\s*(.+)$", line.strip())
        if match:
            key = match.group(1).lower().replace(" ", "_")
            metadata[key] = match.group(2).strip()
    return metadata


def load_documents(documents_dir: Path | None = None) -> list:
    """Load all markdown documents from data/documents/."""
    source = documents_dir or DOCUMENTS_DIR
    if not source.exists():
        raise FileNotFoundError(f"Documents directory not found: {source}")

    loader = DirectoryLoader(
        str(source),
        glob="**/*.md",
        loader_cls=TextLoader,
        loader_kwargs={"encoding": "utf-8"},
        show_progress=True,
    )
    docs = loader.load()

    for doc in docs:
        filename = Path(doc.metadata.get("source", "")).name
        doc.metadata["filename"] = filename
        doc.metadata.update(_parse_frontmatter_metadata(doc.page_content))

    return docs


def split_documents(documents: list) -> list:
    """Split documents into overlapping chunks, preserving metadata."""
    splitter = RecursiveCharacterTextSplitter(
        chunk_size=CHUNK_SIZE,
        chunk_overlap=CHUNK_OVERLAP,
        separators=["\n## ", "\n### ", "\n\n", "\n", " "],
    )
    return splitter.split_documents(documents)


def get_embeddings() -> HuggingFaceEmbeddings:
    """Return the local embedding model (no API key required)."""
    return HuggingFaceEmbeddings(model_name=EMBEDDING_MODEL)


def ingest(
    documents_dir: Path | None = None,
    *,
    reset: bool = True,
) -> Chroma:
    """
    Ingest documents into ChromaDB.

    Parameters
    ----------
    documents_dir : path to markdown files (default: data/documents/)
    reset : if True, delete and recreate the collection
    """
    raw_docs = load_documents(documents_dir)
    chunks = split_documents(raw_docs)
    embeddings = get_embeddings()

    if reset:
        delete_collection_if_exists()

    cloud_kwargs = get_langchain_cloud_kwargs()
    client = None if cloud_kwargs else get_chroma_client()

    vectorstore = Chroma.from_documents(
        documents=chunks,
        embedding=embeddings,
        collection_name=CHROMA_COLLECTION_NAME,
        client=client,
        **cloud_kwargs,
    )

    return vectorstore


def get_vectorstore() -> Chroma:
    """Open an existing ChromaDB collection (after ingest)."""
    cloud_kwargs = get_langchain_cloud_kwargs()
    if cloud_kwargs:
        return Chroma(
            collection_name=CHROMA_COLLECTION_NAME,
            embedding_function=get_embeddings(),
            **cloud_kwargs,
        )
    return Chroma(
        collection_name=CHROMA_COLLECTION_NAME,
        embedding_function=get_embeddings(),
        client=get_chroma_client(),
    )


def retrieve(query: str, top_k: int | None = None) -> list:
    """Retrieve top-k relevant chunks for a query."""
    k = top_k or 4
    vectorstore = get_vectorstore()
    return vectorstore.similarity_search(query, k=k)
