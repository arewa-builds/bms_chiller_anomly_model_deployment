# Step 1 — Knowledge Base & ChromaDB Ingestion

This is **Step 1** of the Manufacturing AI Troubleshooting Copilot. No LLM is used yet — only document ingestion and retrieval.

## What this step does

1. Loads 3 engineering documents from `data/documents/`
2. Splits them into chunks (~1000 chars, 150 overlap)
3. Embeds with `sentence-transformers/all-MiniLM-L6-v2` (local, no API key)
4. Stores in ChromaDB collection **`chiller_troubleshooting`**
5. Lets you test retrieval with a simple script

## Setup

```bash
pip install -r requirements-copilot.txt
```

## Ingest documents

```bash
python scripts/ingest_documents.py
```

## Test retrieval (no LLM)

```bash
python scripts/test_retrieval.py "elevated condenser water approach"
python scripts/test_retrieval.py "tower tracking error FEEDBACK SIGNAL"
python scripts/test_retrieval.py "LOF anomaly score investigation steps"
```

## ChromaDB settings

| Setting | Value |
|---------|-------|
| Collection name | `chiller_troubleshooting` |
| Persist directory | `./chroma_db/` |

## Documents ingested

| File | Type |
|------|------|
| `chiller_operations_manual.md` | Operations manual |
| `cooling_tower_troubleshooting.md` | Troubleshooting guide |
| `chiller_anomaly_investigation_sop.md` | Investigation SOP |

## Interview talking points (Step 1)

- "I started with the knowledge base because RAG quality depends on source documents and chunking."
- "I used metadata (`asset_type`, `doc_type`) parsed from document headers for future filtering."
- "I evaluated retrieval before adding an LLM — if the right chunk isn't retrieved, prompting won't fix it."
- "ChromaDB collection `chiller_troubleshooting` persists locally for fast iteration."

## Next step (not implemented yet)

Step 2: Simple RAG chain — retrieve + LLM + structured output.
