#!/usr/bin/env python3
"""
Verify Chroma Cloud connection and show collection status.

Usage:
    export $(grep -v '^#' .env.copilot | xargs)
    python3 scripts/test_chroma_cloud.py
"""

import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

from copilot.config import CHROMA_COLLECTION_NAME, CHROMA_DATABASE, CHROMA_MODE
from copilot.rag.chroma_client import connection_info, get_chroma_client


def main() -> None:
    if CHROMA_MODE != "cloud":
        print(f"CHROMA_MODE is '{CHROMA_MODE}', not 'cloud'.")
        print("Set CHROMA_MODE=cloud in .env.copilot and export the variables.")
        sys.exit(1)

    print(f"Connecting to {connection_info()} ...")
    client = get_chroma_client()

    collections = client.list_collections()
    names = [c.name for c in collections]
    print(f"✓ Connected. Collections in '{CHROMA_DATABASE}': {names}")

    if CHROMA_COLLECTION_NAME not in names:
        print(f"\nCollection '{CHROMA_COLLECTION_NAME}' not found yet.")
        print("Run: python3 scripts/ingest_documents.py")
        sys.exit(0)

    collection = client.get_collection(name=CHROMA_COLLECTION_NAME)
    count = collection.count()
    print(f"\nCollection '{CHROMA_COLLECTION_NAME}': {count} chunks")

    if count == 0:
        print("\nCollection is empty. Run: python3 scripts/ingest_documents.py")
    else:
        sample = collection.peek(limit=1)
        if sample["documents"]:
            preview = sample["documents"][0][:150].replace("\n", " ")
            print(f"\nSample chunk: {preview}...")


if __name__ == "__main__":
    main()
