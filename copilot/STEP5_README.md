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

```bash
pip install -r requirements-copilot.txt
cp .env.copilot.example .env.copilot
# Fill in OPENAI_API_KEY and Chroma credentials
python3 scripts/ingest_documents.py
```

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
uvicorn copilot.api.main:app --host 0.0.0.0 --port 8002 --reload
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

### 7. Docker Compose

```bash
python3 scripts/ingest_documents.py
docker compose up copilot-api --build -d
curl http://localhost:8002/health
```

**Expected:** `copilot-api` container healthy on port 8002.

### Quick smoke test

```bash
pip install -r requirements-copilot.txt
cp .env.copilot.example .env.copilot
python3 scripts/ingest_documents.py

# Terminal 1
uvicorn copilot.api.main:app --host 0.0.0.0 --port 8002

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
| `Connection refused` on 8002 | Start uvicorn or `docker compose up copilot-api` |
| `openai_configured: false` | Add `OPENAI_API_KEY` to `.env.copilot` |
| Diagnose returns 500 on anomaly | Check API key; run `ingest_documents.py` |
| Empty retrieval / escalate | Re-ingest docs: `python3 scripts/ingest_documents.py` |
| Docker: collection empty | Mount `./chroma_db` volume; ingest before building image |

---

## Files

| File | Purpose |
|------|---------|
| `copilot/api/main.py` | FastAPI app and route handlers |
| `copilot/api/schemas.py` | Request models (`DiagnoseRequest`) |
| `Dockerfile.copilot` | Copilot API container image |
| `docker-compose.yml` | `copilot-api` service on port 8002 |

## Interview talking points (Step 5)

- "I separated the copilot into an API layer so the UI and integrations don't depend on CLI scripts."
- "The API is a thin wrapper over `run_workflow()` — same LangGraph logic, new transport."
- "CORS is enabled for the Step 8 web UI. Health endpoint exposes whether OpenAI is configured."

## Next step

Step 6: Live telemetry bridge — see [`ROADMAP.md`](ROADMAP.md).  
Step 8 UI will consume this API — see [`ROADMAP.md`](ROADMAP.md#ui-application-plan-step-8).
