# Step 5 — FastAPI Copilot Service

Exposes the Step 4 LangGraph workflow as an **HTTP API** so clients (CLI, UI, integrations) can call the copilot without running Python scripts directly.

## Architecture

```
HTTP client (curl, UI, Postman)
    ↓
FastAPI (port 8002)
    ↓
run_workflow() — LangGraph (Step 4)
    ↓
telemetry + ChromaDB + OpenAI
```

## API endpoints

| Endpoint | Method | Description |
|----------|--------|-------------|
| `/health` | GET | Service status + config flags |
| `/scenarios` | GET | List demo telemetry scenario keys |
| `/telemetry/{asset_id}` | GET | Current telemetry snapshot |
| `/diagnose` | POST | Full workflow → `WorkflowResult` |

Interactive docs: **http://localhost:8002/docs**

## Setup

**Local development (full stack):**

```bash
pip install -r requirements-copilot.txt
cp .env.copilot.example .env.copilot
# Fill in OPENAI_API_KEY and Chroma credentials
EMBEDDING_BACKEND=local python3 scripts/ingest_documents.py   # or openai (see below)
```

**Docker API (slim image — no torch / sentence-transformers):**

```bash
cp .env.copilot.example .env.copilot
# Set EMBEDDING_BACKEND=openai and OPENAI_API_KEY
EMBEDDING_BACKEND=openai python3 scripts/ingest_documents.py   # re-ingest with OpenAI embeddings
docker compose up copilot-api --build -d
```

Use the **same** `EMBEDDING_BACKEND` for ingest and retrieval. Re-ingest when switching backends.

| File | Use |
|------|-----|
| `requirements-copilot-api.txt` | API / Docker runtime only (~300–600MB image) |
| `requirements-copilot-ingest.txt` | Ingest with local sentence-transformers |
| `requirements-copilot.txt` | Full local dev (ingest + API) |

---

## Testing CLI commands

Run these in order to verify Step 5 end-to-end.

**Prerequisites**

- Step 1 complete: `python3 scripts/ingest_documents.py`
- `.env.copilot` configured (`OPENAI_API_KEY` for diagnose routes)
- Copilot API running (local or Docker)

| Check | Command | API key? |
|-------|---------|----------|
| Health | `curl http://localhost:8002/health` | No |
| Scenarios | `curl http://localhost:8002/scenarios` | No |
| Telemetry | `curl "http://localhost:8002/telemetry/Chiller-03?scenario=cw_degradation"` | No |
| Diagnose (normal) | `curl -X POST ... /diagnose` with `scenario: normal` | No |
| Diagnose (anomaly) | `curl -X POST ... /diagnose` with `scenario: cw_degradation` | Yes |

### 1. Start the API locally

```bash
python3 -m uvicorn copilot.api.main:app --host 0.0.0.0 --port 8002 --reload
```

Or use the helper script (also works when `uvicorn` is not on your PATH):

```bash
python3 scripts/run_copilot_api.py
python3 scripts/run_copilot_api.py --reload   # auto-reload on code changes
```

**Expected:** Server starts on port 8002. Open http://localhost:8002/docs

### 2. Health check

```bash
curl http://localhost:8002/health
```

**Expected output:**

```json
{
  "status": "ok",
  "service": "chiller-troubleshooting-copilot",
  "version": "1.0.0",
  "chroma_mode": "embedded",
  "embedding_backend": "openai",
  "openai_configured": true
}
```

### 3. List demo scenarios

```bash
curl http://localhost:8002/scenarios
```

**Expected:**

```json
{"scenarios": ["cw_degradation", "flow_restriction", "normal"]}
```

### 4. Get telemetry

```bash
curl "http://localhost:8002/telemetry/Chiller-03?scenario=cw_degradation"
```

**Expected:** JSON with `raw_sensors`, `derived_flags`, and `anomaly` fields.

### 5. Diagnose — normal route (no LLM)

```bash
curl -s -X POST http://localhost:8002/diagnose \
  -H "Content-Type: application/json" \
  -d '{
    "question": "confirm chiller health",
    "asset_id": "Chiller-03",
    "scenario": "normal"
  }' | python3 -m json.tool
```

**Expected:**

- `"route": "normal"`
- `"escalated": false`
- `"diagnosis.confidence": "high"`

### 6. Diagnose — anomaly route (LLM + RAG)

```bash
curl -s -X POST http://localhost:8002/diagnose \
  -H "Content-Type: application/json" \
  -d '{
    "question": "Chiller-03 has elevated anomaly score. What should I investigate?",
    "asset_id": "Chiller-03",
    "scenario": "cw_degradation"
  }' | python3 -m json.tool
```

**Expected:**

- `"route": "diagnose"` or `"escalate"`
- `triage_reason` mentions LOF anomaly and/or elevated flags
- `diagnosis.potential_causes` and `recommended_investigation` populated

### 7. Docker Compose (slim API image)

```bash
cp .env.copilot.example .env.copilot
# EMBEDDING_BACKEND=openai in .env.copilot
EMBEDDING_BACKEND=openai python3 scripts/ingest_documents.py

docker compose up copilot-api --build -d
curl http://localhost:8002/health
```

**OpenAI ingest inside slim container** (no fat image):

```bash
docker compose run --rm copilot-api python3 scripts/ingest_documents.py
```

**Local embeddings ingest** (fat image, optional — no OpenAI embedding cost):

```bash
docker compose --profile ingest run --rm copilot-ingest
```

**Expected:** `copilot-api` container healthy on port 8002. Image should be ~300–600MB (not multi-GB).

### Quick smoke test

```bash
pip install -r requirements-copilot.txt
cp .env.copilot.example .env.copilot
EMBEDDING_BACKEND=openai python3 scripts/ingest_documents.py

# Terminal 1
python3 scripts/run_copilot_api.py

# Terminal 2
curl http://localhost:8002/health
curl "http://localhost:8002/telemetry/Chiller-03?scenario=normal"
curl -s -X POST http://localhost:8002/diagnose \
  -H "Content-Type: application/json" \
  -d '{"question":"health check","asset_id":"Chiller-03","scenario":"normal"}' \
  | python3 -m json.tool
```

### Troubleshooting

| Symptom | Fix |
|---------|-----|
| `uvicorn: command not found` | Use `python3 -m uvicorn ...` (pip installs the module but may not add `~/.local/bin` to PATH) |
| `Connection refused` on 8002 | Start the API with `python3 -m uvicorn ...` or `docker compose up copilot-api` |
| `openai_configured: false` | Add `OPENAI_API_KEY` to `.env.copilot` |
| Diagnose returns 500 on anomaly | Check API key; run `ingest_documents.py` |
| Empty retrieval / escalate | Re-ingest docs: `python3 scripts/ingest_documents.py` |
| Docker build huge / fails | API uses `requirements-copilot-api.txt` only — no sentence-transformers |
| Retrieval returns wrong/empty after Docker | Re-ingest with `EMBEDDING_BACKEND=openai` to match API container |
| `EMBEDDING_BACKEND=openai requires OPENAI_API_KEY` | Add key to `.env.copilot` |
| Want free local embeddings | `EMBEDDING_BACKEND=local` + `pip install -r requirements-copilot-ingest.txt` |

---

## Files

| File | Purpose |
|------|---------|
| `copilot/api/main.py` | FastAPI app and route handlers |
| `copilot/api/schemas.py` | Request models (`DiagnoseRequest`) |
| `scripts/run_copilot_api.py` | Start API without `uvicorn` on PATH |
| `copilot/rag/embeddings.py` | `local` vs `openai` embedding factory |
| `requirements-copilot-api.txt` | Slim API dependencies (Docker) |
| `requirements-copilot-ingest.txt` | Fat ingest dependencies (sentence-transformers) |
| `Dockerfile.copilot` | Slim copilot API image |
| `Dockerfile.copilot-ingest` | Fat one-shot ingest image (local embeddings) |
| `docker-compose.yml` | `copilot-api` + optional `copilot-ingest` profile |

## Interview talking points (Step 5)

- "I separated the copilot into an API layer so the UI and integrations don't depend on CLI scripts."
- "The API is a thin wrapper over `run_workflow()` — same LangGraph logic, new transport."
- "The Docker API image is slim — no torch or sentence-transformers. Query embeddings use OpenAI; ingest runs on the host or in a separate fat container."

## Next step

Step 6: Live telemetry bridge — see [`ROADMAP.md`](ROADMAP.md).  
Step 8 UI will consume this API — see [`ROADMAP.md`](ROADMAP.md#ui-application-plan-step-8).
