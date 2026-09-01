#!/usr/bin/env python3
"""
Step 1 — Ingest engineering documents into ChromaDB.

Usage:
    python scripts/ingest_documents.py
    python scripts/ingest_documents.py --no-reset
"""

import argparse
import sys
from pathlib import Path

# Allow running from repo root without installing the package
sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

from copilot.config import CHROMA_COLLECTION_NAME, CHROMA_PERSIST_DIR, DOCUMENTS_DIR
from copilot.rag.ingest import ingest, load_documents, split_documents


def main() -> None:
    parser = argparse.ArgumentParser(description="Ingest chiller docs into ChromaDB")
    parser.add_argument(
        "--no-reset",
        action="store_true",
        help="Do not delete existing collection before ingest",
    )
    args = parser.parse_args()

    print(f"Documents dir : {DOCUMENTS_DIR}")
    print(f"Chroma persist: {CHROMA_PERSIST_DIR}")
    print(f"Collection    : {CHROMA_COLLECTION_NAME}")
    print()

    raw = load_documents()
    chunks = split_documents(raw)
    print(f"Loaded {len(raw)} documents → {len(chunks)} chunks")
    print()

    ingest(reset=not args.no_reset)
    print(f"✓ Ingested {len(chunks)} chunks into '{CHROMA_COLLECTION_NAME}'")


if __name__ == "__main__":
    main()
