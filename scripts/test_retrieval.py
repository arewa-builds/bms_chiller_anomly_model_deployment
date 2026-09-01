#!/usr/bin/env python3
"""
Step 1 — Test retrieval without an LLM.

Usage:
    python scripts/test_retrieval.py "elevated condenser water approach"
    python scripts/test_retrieval.py "tower tracking error FEEDBACK SIGNAL"
"""

import argparse
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

from copilot.config import RETRIEVAL_TOP_K
from copilot.rag.ingest import retrieve


def main() -> None:
    parser = argparse.ArgumentParser(description="Test ChromaDB retrieval")
    parser.add_argument("query", help="Search query")
    parser.add_argument("-k", type=int, default=RETRIEVAL_TOP_K, help="Top-k results")
    args = parser.parse_args()

    results = retrieve(args.query, top_k=args.k)

    print(f"Query: {args.query!r}")
    print(f"Results: {len(results)}\n")

    for i, doc in enumerate(results, 1):
        meta = doc.metadata
        print(f"--- Result {i} ---")
        print(f"  file      : {meta.get('filename', 'unknown')}")
        print(f"  doc_type  : {meta.get('document_type', meta.get('doc_type', 'n/a'))}")
        print(f"  asset_type: {meta.get('asset_type', 'n/a')}")
        preview = doc.page_content[:300].replace("\n", " ")
        print(f"  preview   : {preview}...")
        print()


if __name__ == "__main__":
    main()
