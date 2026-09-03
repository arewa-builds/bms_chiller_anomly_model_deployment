#!/usr/bin/env python3
"""
Browse the ChromaDB collection — see every stored chunk, metadata, and ID.

Works with embedded mode (local files). Use --sqlite to inspect the raw
SQLite database file directly.

Usage:
    python scripts/inspect_chroma_db.py
    python scripts/inspect_chroma_db.py --full          # show full chunk text
    python scripts/inspect_chroma_db.py --sqlite        # inspect chroma.sqlite3 directly
    python scripts/inspect_chroma_db.py --json            # export as JSON
"""

import argparse
import json
import sqlite3
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

from copilot.env_utils import load_env_copilot

load_env_copilot()

from copilot.config import CHROMA_COLLECTION_NAME, CHROMA_MODE, CHROMA_PERSIST_DIR
from copilot.rag.chroma_client import connection_info, get_chroma_client


def inspect_sqlite() -> None:
    """Show raw contents of chroma.sqlite3 — the actual database file."""
    db_path = Path(CHROMA_PERSIST_DIR) / "chroma.sqlite3"
    if not db_path.exists():
        print(f"SQLite file not found: {db_path}")
        print("Run: python3 scripts/ingest_documents.py")
        sys.exit(1)

    print("=" * 70)
    print("ChromaDB SQLite Inspector (raw database file)")
    print("=" * 70)
    print(f"  File: {db_path}")
    print(f"  Size: {db_path.stat().st_size / 1024:.1f} KB")
    print("=" * 70)

    conn = sqlite3.connect(db_path)
    conn.row_factory = sqlite3.Row

    collections = conn.execute("SELECT id, name FROM collections").fetchall()
    print(f"\nCollections ({len(collections)}):")
    for row in collections:
        print(f"  - {row['name']}  (id: {row['id']})")

    target = conn.execute(
        "SELECT id FROM collections WHERE name = ?", (CHROMA_COLLECTION_NAME,)
    ).fetchone()

    if not target:
        print(f"\nCollection '{CHROMA_COLLECTION_NAME}' not found.")
        conn.close()
        sys.exit(1)

    collection_id = target["id"]
    count = conn.execute(
        "SELECT COUNT(*) FROM embeddings WHERE collection_id = ?",
        (collection_id,),
    ).fetchone()[0]
    print(f"\nChunks in '{CHROMA_COLLECTION_NAME}': {count}")

    # embedding_metadata stores document text and custom metadata
    rows = conn.execute(
        """
        SELECT em.id, em.key, em.string_value
        FROM embedding_metadata em
        JOIN embeddings e ON e.id = em.id
        WHERE e.collection_id = ?
        ORDER BY em.id, em.key
        """,
        (collection_id,),
    ).fetchall()

    # Group by embedding id
    by_id: dict[str, dict] = {}
    for row in rows:
        eid = row["id"]
        by_id.setdefault(eid, {})[row["key"]] = row["string_value"]

    print(f"\nStored chunks:")
    for i, (eid, meta) in enumerate(by_id.items(), 1):
        filename = meta.get("chroma:document", meta.get("filename", "n/a"))
        # Document text is stored under chroma:document in some versions
        doc_key = next((k for k in meta if "document" in k.lower()), None)
        text = meta.get(doc_key, "") if doc_key else ""
        fname = meta.get("filename", "unknown")
        dtype = meta.get("document_type", meta.get("doc_type", "n/a"))
        print(f"\n  [{i}] id={eid[:12]}...")
        print(f"      filename   : {fname}")
        print(f"      doc_type   : {dtype}")
        if text:
            print(f"      text       : {text[:150].replace(chr(10), ' ')}...")

    conn.close()
    print("\n" + "=" * 70)
    print("Open directly: sqlite3 chroma_db/chroma.sqlite3")
    print("=" * 70)


def main() -> None:
    parser = argparse.ArgumentParser(description="Inspect ChromaDB collection contents")
    parser.add_argument("--full", action="store_true", help="Print full document text")
    parser.add_argument("--json", action="store_true", help="Output as JSON")
    parser.add_argument(
        "--sqlite",
        action="store_true",
        help="Inspect the raw chroma.sqlite3 database file",
    )
    args = parser.parse_args()

    if args.sqlite:
        inspect_sqlite()
        return

    client = get_chroma_client()
    connection = connection_info()

    # List all collections in this database
    collections = client.list_collections()
    collection_names = [c.name for c in collections]

    if CHROMA_COLLECTION_NAME not in collection_names:
        print(f"Collection '{CHROMA_COLLECTION_NAME}' not found.")
        print(f"Connection: {connection}")
        print(f"Available collections: {collection_names or '(none)'}")
        print("\nRun: python scripts/ingest_documents.py")
        sys.exit(1)

    collection = client.get_collection(name=CHROMA_COLLECTION_NAME)
    data = collection.get(include=["documents", "metadatas", "embeddings"])

    ids = data["ids"]
    documents = data["documents"]
    metadatas = data["metadatas"]
    embeddings = data["embeddings"]

    if args.json:
        output = {
            "connection": connection,
            "mode": CHROMA_MODE,
            "collection": CHROMA_COLLECTION_NAME,
            "count": len(ids),
            "items": [
                {
                    "id": ids[i],
                    "metadata": metadatas[i],
                    "document": documents[i],
                    "embedding_dims": len(embeddings[i]) if embeddings[i] else 0,
                }
                for i in range(len(ids))
            ],
        }
        print(json.dumps(output, indent=2))
        return

    # Human-readable output
    print("=" * 70)
    print("ChromaDB Inspector")
    print("=" * 70)
    print(f"  Mode       : {CHROMA_MODE}")
    print(f"  Connection : {connection}")
    print(f"  Collection : {CHROMA_COLLECTION_NAME}")
    print(f"  Chunks     : {len(ids)}")
    if embeddings is not None and len(embeddings) > 0 and embeddings[0] is not None:
        print(f"  Vector dim : {len(embeddings[0])}")
    print("=" * 70)

    for i, doc_id in enumerate(ids):
        meta = metadatas[i] or {}
        text = documents[i] or ""

        print(f"\n[{i + 1}/{len(ids)}] ID: {doc_id}")
        print(f"  filename   : {meta.get('filename', 'n/a')}")
        print(f"  doc_type   : {meta.get('document_type', meta.get('doc_type', 'n/a'))}")
        print(f"  asset_type : {meta.get('asset_type', 'n/a')}")

        if args.full:
            print("  --- document text ---")
            for line in text.splitlines():
                print(f"    {line}")
        else:
            preview = text[:200].replace("\n", " ")
            print(f"  preview    : {preview}...")

    print("\n" + "=" * 70)
    print("Tips:")
    print("  --full    show complete chunk text")
    print("  --json    export all data as JSON")
    print("  --sqlite  inspect the raw chroma.sqlite3 file directly")
    print("=" * 70)


if __name__ == "__main__":
    main()
