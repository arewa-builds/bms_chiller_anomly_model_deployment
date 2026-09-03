# Copilot Roadmap — Steps 5–9 & Web UI Plan

> **Saved for future context.** Steps 6–9 are **proposed** extensions.
> Steps 1–5 are complete. Step 5 is the FastAPI copilot service.

---

## Current status (Steps 1–5)

| Step | Status | Description |
|------|--------|-------------|
| 1 | Done | Knowledge base ingestion + ChromaDB retrieval |
| 2 | Done | RAG chain with structured LLM output |
| 3 | Done | Telemetry tool with derived flags |
| 4 | Done | LangGraph workflow with conditional routing and escalation |
| 5 | Done | FastAPI copilot service + docker-compose integration |

---

## Proposed Steps 6–9

| Step | Name | What it adds |
|------|------|--------------|
| **5** | FastAPI copilot service | HTTP API wrapping `run_workflow()` — `POST /diagnose`, health check, docker-compose service |
| **6** | Live telemetry bridge | Replace demo scenarios with real data from OPC UA bridge or LOF inference stack |
| **7** | Alerting & notifications | Fire alerts when anomaly/escalation occurs (webhook, email, Slack); extend `handle_anomaly()` |
| **8** | Engineer web UI | Browser app for questions, telemetry view, and structured diagnosis |
| **9** | History, auth & production polish | Session history, user auth, audit log, deployment hardening, optional dashboard trends |

### Step 5 — FastAPI copilot service

- Expose `run_workflow()` as HTTP endpoints
- `GET /health`, `GET /telemetry/{asset_id}`, `POST /diagnose`, `GET /scenarios` (demo mode)
- Add `copilot-api` service to `docker-compose.yml` (port 8002)
- Prerequisite for Step 8 UI

### Step 6 — Live telemetry bridge

- Wire `get_chiller_telemetry()` to real OPC UA reads or cached inference results
- Remove dependency on `--scenario` for production use
- Keep demo scenarios as a `demo` mode for interviews/demos

### Step 7 — Alerting & notifications

- Trigger notifications when `route=escalate` or LOF flags anomaly
- Configurable channels (webhook first, then email/Slack)
- Align with escalation criteria in `data/documents/chiller_anomaly_investigation_sop.md`

### Step 8 — Engineer web UI

- Replace CLI with a browser interface (see UI plan below)
- Depends on Step 5 API being in place
- Can start with demo scenarios before Step 6 live telemetry

### Step 9 — History, auth & production polish

- Store past diagnoses and telemetry snapshots
- Basic auth / API keys for the copilot service
- Logging, monitoring, deployment docs for production handoff

---

## UI Application Plan (Step 8)

**Goal:** A web app where a BMS engineer can ask troubleshooting questions, see live telemetry, and get structured diagnoses — without using the CLI.

### Architecture

```
Browser (React + Vite)
    ↓ HTTP
FastAPI copilot service (Step 5)
    ↓
LangGraph workflow (Step 4) + telemetry + ChromaDB + OpenAI
```

Build the UI against the Step 5 API, not by calling Python scripts directly.

---

### Phase 1 — API contract (prerequisite: Step 5)

| Endpoint | Method | Purpose |
|----------|--------|---------|
| `/health` | GET | Service status |
| `/telemetry/{asset_id}` | GET | Current sensor snapshot + derived flags |
| `/diagnose` | POST | Question + asset → `WorkflowResult` |
| `/scenarios` | GET | List demo scenarios (dev/demo mode only) |

`POST /diagnose` request body:

```json
{
  "question": "Chiller-03 has elevated anomaly score. What should I investigate?",
  "asset_id": "Chiller-03",
  "scenario": "cw_degradation"
}
```

Response: `WorkflowResult` (route, triage_reason, escalated, telemetry, diagnosis).

---

### Phase 2 — UI screens

**Screen 1: Dashboard / Ask**
- Asset selector (`Chiller-03`, etc.)
- Scenario selector (demo mode only — hidden in production)
- Text area for the engineer question
- Submit button → calls `POST /diagnose`

**Screen 2: Telemetry panel** (sidebar or top card)
- Raw sensors (16 values)
- Derived flags with elevated / value / timestamp
- LOF anomaly score and label
- Auto-refresh or manual refresh via `GET /telemetry`

**Screen 3: Diagnosis results**
- Route badge (`normal` / `diagnose` / `escalate`)
- Triage reason
- Condition, confidence, escalation flag
- Potential causes (ranked list)
- Evidence bullets
- Recommended investigation steps
- Source citations (manual links)

**Screen 4: Escalation highlight**
- When `escalated=true`, show a prominent alert banner
- Escalation steps at the top of investigation list

---

### Phase 3 — Tech stack

| Option | Pros | Cons |
|--------|------|------|
| **React + Vite** | Modern, component-based, good for interviews | More setup |
| **Streamlit** | Fastest to build in Python | Less polished, harder to customize |
| **HTMX + FastAPI templates** | Minimal JS, same FastAPI app | Less interactive |
| **Gradio** | Very fast for demos | Looks like ML demo, not a product |

**Recommended:** React + Vite frontend in `ui/`, talking to FastAPI on port 8002.

---

### Phase 4 — Proposed file structure

```
ui/
├── src/
│   ├── components/
│   │   ├── TelemetryPanel.tsx
│   │   ├── DiagnosisResult.tsx
│   │   ├── AskForm.tsx
│   │   └── EscalationBanner.tsx
│   ├── api/copilot.ts          # fetch wrappers for FastAPI
│   └── App.tsx
├── package.json
└── vite.config.ts

copilot/
├── api/
│   ├── main.py                 # FastAPI app (Step 5)
│   └── routes/
│       ├── diagnose.py
│       └── telemetry.py
```

---

### Phase 5 — Docker integration

Add to `docker-compose.yml`:

```yaml
copilot-api:     # port 8002 — FastAPI
copilot-ui:      # port 3000 — React (nginx in prod)
chroma:          # port 8001 — already exists
lof-chiller:     # port 8000 — already exists
```

---

### Phase 6 — UX details

- **Loading states** while RAG + LLM runs (5–15s)
- **Example questions** as clickable chips ("elevated CW approach", "tower tracking error")
- **Route explanation** — show why triage chose `normal` vs `diagnose`
- **JSON toggle** — "View raw response" for debugging/demo
- **Demo mode banner** — when using scenario, show "Demo data — not live BMS"

---

### Phase 7 — Testing plan (for STEP8_README)

- Manual: submit question for each scenario, verify UI matches CLI output
- API: `curl POST /diagnose` matches `ask_copilot.py --json`
- E2E (optional): Playwright smoke test for ask → result flow

---

### Suggested build order

1. **Step 5** — FastAPI service (required foundation)
2. **Step 8 UI** — can start with demo scenarios before Step 6 live telemetry
3. **Step 6** — swap demo telemetry for live OPC UA data in the API
4. **Step 7** — add alert button/webhook from UI when escalated
5. **Step 9** — auth, history, production polish

---

### Deferred (out of scope for v1)

- Real-time WebSocket telemetry (polling is fine for v1)
- Multi-asset fleet view
- User accounts / RBAC (Step 9)
- Mobile app

---

## Related docs

| Doc | Purpose |
|-----|---------|
| [`STEP1_README.md`](STEP1_README.md) | ChromaDB ingestion |
| [`STEP2_README.md`](STEP2_README.md) | RAG chain |
| [`STEP3_README.md`](STEP3_README.md) | Telemetry tool |
| [`STEP4_README.md`](STEP4_README.md) | LangGraph workflow |
| [`STEP_README_TEMPLATE.md`](STEP_README_TEMPLATE.md) | Required README format for new steps |
| [`../README.md`](../README.md) | Root project overview |

---

*Last updated: 2026-09-02*
