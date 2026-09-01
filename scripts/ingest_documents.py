#!/usr/bin/env python3
"""
Step 1 — Ingest engineering documents into ChromaDB.

Usage:
    python3 scripts/ingest_documents.py
    python3 scripts/ingest_documents.py --no-reset

Chroma Cloud:
    cp .env.copilot.example .env.copilot   # fill in API key + tenant
    export $(grep -v '^#' .env.copilot | xargs)
    python3 scripts/ingest_documents.py
    python3 scripts/test_chroma_cloud.py
"""

import argparse
import sys
from pathlib import Path

# Allow running from repo root without installing the package
sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

# Load .env.copilot via the shared config loader so values are normalized
# (e.g., CHROMA_MODE="cloud" becomes "cloud" instead of '"cloud"').
from copilot.config import CHROMA_COLLECTION_NAME, CHROMA_MODE, DOCUMENTS_DIR
from copilot.rag.chroma_client import connection_info
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
    print(f"Chroma        : {connection_info()}")
    print(f"Collection    : {CHROMA_COLLECTION_NAME}")
    if CHROMA_MODE == "cloud":
        print("Target        : Chroma Cloud (BMS database)")
    print()

    raw = load_documents()
    chunks = split_documents(raw)
    print(f"Loaded {len(raw)} documents → {len(chunks)} chunks")
    print()

    ingest(reset=not args.no_reset)
    print(f"✓ Ingested {len(chunks)} chunks into '{CHROMA_COLLECTION_NAME}'")


if __name__ == "__main__":
    main()
