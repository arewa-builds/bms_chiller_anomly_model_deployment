# BMS Chiller Anomaly Detection & AI Troubleshooting Copilot

Production deployment package for **BMS chiller anomaly detection** plus a **Manufacturing AI Troubleshooting Copilot** built on RAG (Retrieval-Augmented Generation).

The system has two integrated layers:

1. **LOF inference pipeline** — reads 16 raw sensor values, engineers 197 features, and scores them with a Local Outlier Factor model exported to ONNX.
2. **Troubleshooting copilot** — retrieves engineering documentation from ChromaDB, pulls live (or demo) telemetry, and returns a structured diagnosis via an LLM.

---

## Architecture

```
┌─────────────────────────────────────────────────────────────────────────┐
│                         BMS / Field Layer                               │
│  OPC UA Server (16 sensors)  →  opcua_bridge.py  →  preprocessor.py   │
└────────────────────────────────────────┬────────────────────────────────┘
                                         │ 197 features
                                         ▼
┌─────────────────────────────────────────────────────────────────────────┐
│                      LOF Inference (FastAPI + ONNX)                       │
│  POST /predict  ·  POST /predict/batch  ·  GET /health                  │
└────────────────────────────────────────┬────────────────────────────────┘
                                         │ anomaly score + label
                                         ▼
┌─────────────────────────────────────────────────────────────────────────┐
│                   Manufacturing AI Troubleshooting Copilot              │
│                                                                         │
│  telemetry tool  →  ChromaDB retriever  →  ChatOpenAI (structured)    │
│       ↑                    ↑                                            │
│  demo scenarios      engineering docs (3 manuals/SOPs)                  │
└─────────────────────────────────────────────────────────────────────────┘
```

---

## Repository layout

```
├── app/
│   ├── main.py                   # FastAPI inference server (ONNX Runtime)
│   ├── preprocessor.py         # ChillerPreprocessor — 16 sensors → 197 features
│   ├── opcua_bridge.py           # asyncua client, 30-min poll → /predict
│   ├── mock_data_generator.py    # Synthetic chiller data for dev/test
│   └── score_synthetic_data.py     # Batch-score synthetic CSV with ONNX model
├── model/
│   └── lof_chiller_model.onnx    # Trained LOF model
├── copilot/
│   ├── api/                      # FastAPI service (Step 5)
│   ├── workflow/                 # LangGraph routing (Step 4)
│   ├── rag/                      # Ingestion, embeddings, ChromaDB, RAG chain
│   ├── tools/telemetry.py        # get_chiller_telemetry() demo tool
│   ├── data/demo_scenarios.py    # cw_degradation, flow_restriction, normal
│   ├── schemas.py                # Pydantic models (telemetry + diagnosis)
│   ├── prompts.py                # Grounding prompts
│   ├── ROADMAP.md                # Steps 6–9 and UI plan
│   ├── STEP1_README.md … STEP5_README.md
├── data/documents/               # Engineering docs for RAG ingestion
├── scripts/
│   ├── ingest_documents.py       # Chunk + embed + store in ChromaDB
│   ├── inspect_chroma_db.py      # Browse stored chunks
│   ├── test_retrieval.py         # Retrieval smoke test (no LLM)
│   ├── test_chroma_cloud.py      # Verify Chroma Cloud connection
│   ├── ask_copilot.py            # CLI — retrieval, telemetry, full diagnosis
│   └── run_copilot_api.py        # Start Step 5 API (no uvicorn on PATH)
├── synthetic_chiller_data.csv    # 1000-row synthetic sensor dataset
├── synthetic_chiller_data_scored.csv
├── Dockerfile                    # LOF inference API container
├── Dockerfile.copilot            # Slim copilot API (no torch)
├── Dockerfile.copilot-ingest     # Fat ingest image (sentence-transformers)
├── docker-compose.yml            # Inference, bridge, Chroma, copilot-api
├── requirements.txt              # Inference / bridge dependencies
├── requirements-copilot.txt      # Full local dev (ingest + API + CLI)
├── requirements-copilot-api.txt  # Slim API / Docker runtime only
└── requirements-copilot-ingest.txt  # Ingest with local embeddings
```

---

## Quick start — LOF inference API

### Build and run

```bash
docker build -t lof-chiller:2.0 .
docker run -p 8000:8000 lof-chiller:2.0
```

### Health check

```bash
curl http://localhost:8000/health
```

### Score a reading

```bash
curl -X POST http://localhost:8000/predict \
  -H "Content-Type: application/json" \
  -d '{"features": [0.0, 0.0, ...]}'   # exactly 197 float values
```

### API endpoints

| Endpoint | Method | Description |
|----------|--------|-------------|
| `/health` | GET | Liveness check + model metadata |
| `/predict` | POST | Score one sensor reading |
| `/predict/batch` | POST | Score multiple readings at once |

**Example response:**

```json
{
  "label": 1,
  "decision_score": 1.587,
  "is_anomaly": false,
  "inference_ms": 6.6
}
```

`label` is `+1` for normal, `-1` for anomaly. `decision_score` above 0 is normal.

### Full stack (inference + OPC-UA bridge)

```bash
docker compose up --build
```

Before connecting to a live BMS server, configure `app/opcua_bridge.py`:

1. Set `OPC_SERVER_URL` (or pass via `docker-compose.yml` environment).
2. Fill in all 16 entries in `NODE_MAP` with live BMS node IDs.
3. Mount `model/scaler.pkl` from training artifacts.
4. Extend `handle_anomaly()` for your notification channel.

---

## Quick start — Troubleshooting copilot

### Setup

```bash
pip install -r requirements-copilot.txt   # full local dev
cp .env.copilot.example .env.copilot
# Fill in CHROMA credentials and OPENAI_API_KEY
```

| Install target | Command | When to use |
|----------------|---------|-------------|
| Full local dev | `pip install -r requirements-copilot.txt` | CLI, ingest, API on host |
| API / Docker only | `pip install -r requirements-copilot-api.txt` | Slim runtime, no torch |
| Ingest (local embeddings) | `pip install -r requirements-copilot-ingest.txt` | sentence-transformers ingest |

**Embeddings:** Set `EMBEDDING_BACKEND` in `.env.copilot`. Use `local` (default) on the host with sentence-transformers, or `openai` for the slim Docker API. **Ingest and retrieval must use the same backend** — re-ingest when switching.

### Step 1 — Ingest engineering docs into ChromaDB

```bash
# local embeddings (default)
python3 scripts/ingest_documents.py

# or OpenAI embeddings (matches Docker API)
EMBEDDING_BACKEND=openai python3 scripts/ingest_documents.py

python3 scripts/test_retrieval.py "elevated condenser water approach"
```

See [`copilot/STEP1_README.md`](copilot/STEP1_README.md) for embedded, server, and Chroma Cloud modes.

### Step 2 — RAG diagnosis with structured LLM output

```bash
python3 scripts/ask_copilot.py --retrieve-only "tower tracking error"
python3 scripts/ask_copilot.py --json --asset Chiller-03 \
  "Chiller-03 has an elevated anomaly score. What should I investigate?"
```

See [`copilot/STEP2_README.md`](copilot/STEP2_README.md).

### Step 3 — Telemetry + RAG diagnosis

```bash
python3 scripts/ask_copilot.py --telemetry-only --scenario cw_degradation
python3 scripts/ask_copilot.py --json --asset Chiller-03 --scenario cw_degradation \
  "elevated CW approach and tower tracking error — what should I check?"
```

Telemetry returns **derived flags** with elevation status, measured value, and timestamp:

```json
"derived_flags": {
  "cw_approach_to_wb_elevated": {"elevated": true, "value": 8, "timestamp": "2026-09-01T14:00:00Z"},
  "flow_imbalance_pct_high": {"elevated": true, "value": 10, "timestamp": "2026-09-01T14:00:00Z"},
  "tower_tracking_error_abs_high": {"elevated": true, "value": 12, "timestamp": "2026-09-01T14:00:00Z"}
}
```

Demo scenarios: `cw_degradation`, `flow_restriction`, `normal`.

See [`copilot/STEP3_README.md`](copilot/STEP3_README.md).

### Step 4 — LangGraph workflow with routing and escalation

```bash
# Normal route — no LLM call
python3 scripts/ask_copilot.py --scenario normal "confirm chiller health"

# Anomaly route — telemetry + RAG + conditional escalation
python3 scripts/ask_copilot.py --json --scenario cw_degradation \
  "what should I investigate?"
```

See [`copilot/STEP4_README.md`](copilot/STEP4_README.md).

### Step 5 — FastAPI copilot service

```bash
python3 scripts/run_copilot_api.py
# or: python3 -m uvicorn copilot.api.main:app --host 0.0.0.0 --port 8002

curl http://localhost:8002/health
curl -s -X POST http://localhost:8002/diagnose \
  -H "Content-Type: application/json" \
  -d '{"question":"health check","asset_id":"Chiller-03","scenario":"normal"}'
```

**Docker (slim image — no torch / sentence-transformers):**

```bash
EMBEDDING_BACKEND=openai python3 scripts/ingest_documents.py   # re-ingest once
docker compose up copilot-api --build -d
```

API docs: http://localhost:8002/docs

See [`copilot/STEP5_README.md`](copilot/STEP5_README.md) for ingest options, image sizes, and troubleshooting.

### Copilot smoke test (all steps)

```bash
pip install -r requirements-copilot.txt
cp .env.copilot.example .env.copilot
EMBEDDING_BACKEND=local python3 scripts/ingest_documents.py
python3 scripts/ask_copilot.py --telemetry-only --scenario cw_degradation
python3 scripts/ask_copilot.py --json --asset Chiller-03 --scenario cw_degradation \
  "Chiller-03 has elevated anomaly score. What should I investigate?"
```

---

## Model facts

| Property | Value |
|----------|-------|
| Algorithm | Local Outlier Factor |
| Format | ONNX (Runtime 1.18) |
| Raw sensors | 16 (OPC UA) |
| Engineered features | 197 |
| Decision threshold | 0.0 (positive score = normal) |
| Label | +1 normal, −1 anomaly |
| Poll interval | 30 minutes (`POLL_INTERVAL_S = 1800`) |
| Warm-up | 48 readings (24 h) before first inference |
| Avg inference latency | ~6.6 ms |

**Units:** Temperatures in °F, RLA in %, flow in gal/min — must match training data.

---

## Knowledge base documents

| File | Type |
|------|------|
| `chiller_operations_manual.md` | Operations manual |
| `cooling_tower_troubleshooting.md` | Troubleshooting guide |
| `chiller_anomaly_investigation_sop.md` | Investigation SOP |

Ingested into ChromaDB collection **`chiller_troubleshooting`** (~13 chunks).

---

## Docker Compose services

| Service | Port | Purpose |
|---------|------|---------|
| `lof-chiller` | 8000 | ONNX inference API |
| `opcua-bridge` | — | Polls OPC UA, posts to `/predict` |
| `chroma` | 8001 | ChromaDB server for copilot RAG (optional) |
| `copilot-api` | 8002 | Slim copilot FastAPI (`EMBEDDING_BACKEND=openai`) |
| `copilot-ingest` | — | One-shot fat ingest (`--profile ingest`, local embeddings) |

```bash
docker compose up --build              # inference + bridge
docker compose up chroma -d            # Chroma server only
docker compose up copilot-api --build  # slim copilot API
docker compose --profile ingest run --rm copilot-ingest   # local-embedding ingest
```

---

## Configuration reference

| Variable | Default | Description |
|----------|---------|-------------|
| `CHROMA_MODE` | `embedded` | `embedded`, `server`, or `cloud` |
| `CHROMA_COLLECTION_NAME` | `chiller_troubleshooting` | Vector collection name |
| `EMBEDDING_BACKEND` | `local` | `local` (sentence-transformers) or `openai` (Docker API) |
| `EMBEDDING_MODEL` | `all-MiniLM-L6-v2` | HuggingFace model when `EMBEDDING_BACKEND=local` |
| `OPENAI_EMBEDDING_MODEL` | `text-embedding-3-small` | OpenAI model when `EMBEDDING_BACKEND=openai` |
| `OPENAI_API_KEY` | — | Required for LLM diagnosis and OpenAI embeddings |
| `OPENAI_MODEL` | `gpt-4o-mini` | LLM for structured output |
| `OPC_SERVER_URL` | `opc.tcp://127.0.0.1:4840` | BMS OPC UA endpoint |
| `POLL_INTERVAL_S` | `1800` | Bridge poll interval (seconds) |

Copy `.env.copilot.example` → `.env.copilot` for copilot settings. Scripts load it automatically.

---

## Structured diagnosis output

The copilot returns a `TroubleshootingDiagnosis` JSON object:

| Field | Description |
|-------|-------------|
| `asset` | Equipment ID |
| `condition` | Summary of the problem |
| `potential_causes` | Ranked likely causes |
| `evidence` | Facts from telemetry and retrieved docs |
| `recommended_investigation` | Field investigation steps |
| `confidence` | `high` / `medium` / `low` |
| `sources` | Cited manuals and SOPs |
| `escalation_required` | True when evidence is insufficient |

---

## Security

- Do not commit OPC UA certificates, private keys, or production credentials.
- Use environment variables or mounted secrets for sensitive configuration.
- Prefer `SignAndEncrypt` security policies in production OPC UA connections.
- Keep `.env.copilot` out of version control (use `.env.copilot.example` as a template).

---

## Roadmap

| Step | Status | Description |
|------|--------|-------------|
| 1 | Done | Knowledge base ingestion + ChromaDB retrieval |
| 2 | Done | RAG chain with structured LLM output |
| 3 | Done | Telemetry tool with derived flags |
| 4 | Done | LangGraph workflow with conditional routing and escalation |
| 5 | Done | FastAPI copilot service + docker-compose integration |
| 6–9 | Planned | See [`copilot/ROADMAP.md`](copilot/ROADMAP.md) for live telemetry, alerting, web UI, and production polish |
