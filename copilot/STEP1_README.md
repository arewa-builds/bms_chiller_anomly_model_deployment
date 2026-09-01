# Step 1 — Knowledge Base & ChromaDB Ingestion

This is **Step 1** of the Manufacturing AI Troubleshooting Copilot. No LLM is used yet — only document ingestion and retrieval.

## What this step does

1. Loads 3 engineering documents from `data/documents/`
2. Splits them into chunks (~1000 chars, 150 overlap)
3. Embeds with `sentence-transformers/all-MiniLM-L6-v2` (local, no API key)
4. Stores in ChromaDB collection **`chiller_troubleshooting`**
5. Lets you test retrieval and **inspect the database**

## Setup

```bash
pip install -r requirements-copilot.txt
```

---

## Option A — Embedded mode (simplest)

Database stored as local files in `./chroma_db/`.

```bash
python3 scripts/ingest_documents.py
python3 scripts/inspect_chroma_db.py
python3 scripts/test_retrieval.py "elevated condenser water approach"
```

---

## Option B — Chroma Server mode (see the actual database)

Runs Chroma as a **real database service** you can browse via API.

### 1. Start Chroma server

```bash
docker compose up chroma -d
```

### 2. Point scripts at the server

```bash
export CHROMA_MODE=server
export CHROMA_HOST=localhost
export CHROMA_PORT=8001
```

Or copy `.env.copilot.example` → `.env.copilot` and run:

```bash
export $(grep -v '^#' .env.copilot | xargs)
```

### 3. Ingest and inspect

```bash
python3 scripts/ingest_documents.py
python3 scripts/inspect_chroma_db.py
python3 scripts/inspect_chroma_db.py --full    # see full chunk text
python3 scripts/inspect_chroma_db.py --json  # export as JSON
```

## See the actual database

### Method 1 — Inspector script (recommended)

```bash
python3 scripts/inspect_chroma_db.py           # all chunks + previews
python3 scripts/inspect_chroma_db.py --full  # full chunk text
python3 scripts/inspect_chroma_db.py --json  # export everything as JSON
```

### Method 2 — Raw SQLite file

Chroma stores metadata and document text in `chroma_db/chroma.sqlite3`:

```bash
python3 scripts/inspect_chroma_db.py --sqlite

# Or open directly:
sqlite3 chroma_db/chroma.sqlite3
sqlite> SELECT name FROM collections;
sqlite> SELECT COUNT(*) FROM embeddings;
sqlite> .quit
```

### Method 3 — Chroma Server + REST API (optional)

```bash
docker compose up chroma -d
```

Then open **http://localhost:8001/docs** in your browser to explore the REST API.

> **Note:** Use embedded mode (`CHROMA_MODE=embedded`, the default) for ingest and inspect.
> Server mode is for exploring the REST API; re-ingest after starting the server if the collection is empty.

## ChromaDB settings

| Setting | Default | Description |
|---------|---------|-------------|
| `CHROMA_MODE` | `embedded` | `embedded` or `server` |
| `CHROMA_HOST` | `localhost` | Server hostname |
| `CHROMA_PORT` | `8001` | Server port (8001 avoids conflict with chiller API on 8000) |
| Collection name | `chiller_troubleshooting` | Your vector collection |
| Persist directory | `./chroma_db/` | Used by both embedded mode and Docker volume |

## Where is the data stored?

Both modes use the same folder on disk:

```
chroma_db/
├── chroma.sqlite3          ← metadata, document text, collection info
└── <uuid>/                 ← vector index (binary files)
    ├── data_level0.bin
    ├── header.bin
    └── ...
```

In **server mode**, Chroma reads/writes this folder inside the Docker container (mounted from `./chroma_db`).

## Documents ingested

| File | Type |
|------|------|
| `chiller_operations_manual.md` | Operations manual |
| `cooling_tower_troubleshooting.md` | Troubleshooting guide |
| `chiller_anomaly_investigation_sop.md` | Investigation SOP |

## Interview talking points (Step 1)

- "I started with the knowledge base because RAG quality depends on source documents and chunking."
- "Chroma runs embedded for local dev or as a server for production-like access."
- "I validated retrieval and inspected stored chunks before adding an LLM."

## Next step (not implemented yet)

Step 2: Simple RAG chain — retrieve + LLM + structured output.
