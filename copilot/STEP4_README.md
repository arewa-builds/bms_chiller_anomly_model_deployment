# Step 4 — LangGraph Workflow

Replaces the linear Step 3 chain with a **LangGraph state machine** that routes based on telemetry triage and escalates when evidence is weak.

## Architecture

```
Engineer question
    ↓
fetch_telemetry
    ↓
triage ──normal──→ normal_ack ──→ END  (no LLM, no retrieval)
    │
    └──diagnose──→ retrieve → diagnose ──low confidence / no docs──→ escalate → END
                              │
                              └── sufficient evidence ──→ END
```

## Routing rules

### Triage (telemetry-based)

| Condition | Route | LLM called? |
|-----------|-------|-------------|
| No anomaly + no elevated flags + `normal` scenario | `normal` | No |
| LOF anomaly or any elevated derived flag | `diagnose` | Yes |

### Post-diagnosis escalation

Escalation runs when any of these are true after the LLM diagnosis:

- No documentation chunks retrieved
- `escalation_required` is true in the LLM response
- `confidence` is `low`

The escalate node prepends SOP-aligned escalation steps and sets `escalation_required=true`.

## Setup

```bash
pip install -r requirements-copilot.txt
cp .env.copilot.example .env.copilot
# OPENAI_API_KEY required for diagnose route only
EMBEDDING_BACKEND=local python3 scripts/ingest_documents.py
```

LangGraph is the **default** path in `ask_copilot.py`. Use `--linear` for the Step 3 chain. The same workflow is available via `POST /diagnose` on the Step 5 API — see [`STEP5_README.md`](STEP5_README.md).

Embedding backend must match Step 1 ingest (`local` or `openai`). See [`STEP1_README.md`](STEP1_README.md).

---

## Testing CLI commands

Run these in order to verify Step 4 end-to-end.

**Prerequisites**

- Step 1 complete: `python3 scripts/ingest_documents.py`
- `.env.copilot` configured (only needed for `diagnose` / `escalate` routes)
- `OPENAI_API_KEY` set for any command that hits the LLM

| Route | Scenario | API key needed? | LLM called? |
|-------|----------|-----------------|-------------|
| `normal` | `normal` | No | No |
| `diagnose` | `cw_degradation`, `flow_restriction` | Yes | Yes |
| `escalate` | any diagnose route where confidence is low | Yes | Yes (then escalate node) |

### 1. Normal route (no LLM, no retrieval)

```bash
python3 scripts/ask_copilot.py --scenario normal \
  "confirm chiller health"
```

**Expected output:**

- `Route: normal`
- `Triage: No LOF anomaly and no elevated derived flags — steady-state operation`
- `Escalated: False`
- `Confidence: high`
- No `Sources` listed (retrieval was skipped)

JSON:

```bash
python3 scripts/ask_copilot.py --json --scenario normal \
  "confirm chiller health"
```

Verify JSON fields: `route`, `triage_reason`, `escalated`, `telemetry`, `diagnosis`.

### 2. Diagnose route (telemetry + retrieval + LLM)

```bash
python3 scripts/ask_copilot.py --scenario cw_degradation \
  "Chiller-03 has elevated anomaly score. What should I investigate?"

python3 scripts/ask_copilot.py --scenario flow_restriction \
  "condenser flow is low — what should I check?"
```

**Expected output:**

- `Route: diagnose` or `escalate` (depends on LLM confidence)
- `Triage` mentions LOF anomaly and/or elevated derived flags
- `potential_causes`, `evidence`, and `recommended_investigation` populated
- `Sources` lists retrieved manuals/SOPs

JSON with full workflow metadata:

```bash
python3 scripts/ask_copilot.py --json --scenario cw_degradation \
  "elevated CW approach and tower tracking error"
```

### 3. Escalation route

Escalation is triggered automatically when the LLM returns low confidence, sets `escalation_required`, or when no docs are retrieved.

To observe escalation, run a diagnose-route scenario and check output:

```bash
python3 scripts/ask_copilot.py --json --scenario cw_degradation \
  "what should I investigate?"
```

**Expected when escalated:**

- `route: "escalate"` or `escalated: true`
- `escalation_required: true` in `diagnosis`
- First `recommended_investigation` step starts with `ESCALATE:`

### 4. Compare LangGraph vs Step 3 linear chain

```bash
# Step 4 — LangGraph (default)
python3 scripts/ask_copilot.py --scenario cw_degradation \
  "elevated CW approach"

# Step 3 — linear chain (no routing)
python3 scripts/ask_copilot.py --linear --scenario cw_degradation \
  "elevated CW approach"
```

Linear mode always calls the LLM even for `normal` scenarios. LangGraph short-circuits normal operation.

### 5. Triage-only verification (no CLI flag — Python)

```bash
python3 -c "
from copilot.tools.telemetry import get_chiller_telemetry
from copilot.workflow.triage import triage_telemetry
for s in ['normal', 'cw_degradation', 'flow_restriction']:
    t = get_chiller_telemetry('Chiller-03', scenario=s)
    print(s, '->', triage_telemetry(t))
"
```

**Expected:**

```
normal -> ('normal', 'No LOF anomaly and no elevated derived flags ...')
cw_degradation -> ('diagnose', 'LOF anomaly with elevated flags: ...')
flow_restriction -> ('diagnose', 'LOF anomaly with elevated flags: flow_imbalance_pct_high')
```

### 6. Graph compilation smoke test

```bash
python3 -c "
from copilot.workflow.graph import build_workflow
g = build_workflow()
print('nodes:', list(g.get_graph().nodes))
"
```

**Expected nodes:** `fetch_telemetry`, `triage`, `normal_ack`, `retrieve`, `diagnose`, `escalate`

### Quick smoke test

```bash
pip install -r requirements-copilot.txt
cp .env.copilot.example .env.copilot
EMBEDDING_BACKEND=local python3 scripts/ingest_documents.py

# Normal path — no API key needed
python3 scripts/ask_copilot.py --scenario normal "health check"

# Anomaly path — needs OPENAI_API_KEY
python3 scripts/ask_copilot.py --json --scenario cw_degradation \
  "what should I investigate?"
```

### Troubleshooting

| Symptom | Fix |
|---------|-----|
| `Configuration error: OPENAI_API_KEY` | Add key to `.env.copilot` (only needed for diagnose route) |
| `No relevant documentation retrieved` | Re-ingest; check `EMBEDDING_BACKEND` matches ingest |
| `EMBEDDING_BACKEND=openai requires OPENAI_API_KEY` | Add key when using OpenAI embeddings |
| Always routes to `diagnose` on normal | Pass `--scenario normal` explicitly |
| Want Step 3 behavior | Add `--linear` flag |

---

## Files

| File | Purpose |
|------|---------|
| `copilot/workflow/graph.py` | LangGraph nodes, edges, `run_workflow()` |
| `copilot/workflow/triage.py` | Telemetry triage and post-diagnosis escalation rules |
| `copilot/workflow/state.py` | `CopilotState` TypedDict |
| `copilot/schemas.py` | `WorkflowResult` model |

## Interview talking points (Step 4)

- "I moved from a linear chain to LangGraph so routing is explicit and testable — normal operation skips the LLM entirely."
- "Triage uses telemetry (LOF score + derived flags), not just the user question."
- "Escalation is a separate graph node triggered by low confidence or missing retrieval — not just a prompt instruction."

## Next step

Step 5: FastAPI copilot service — see [`STEP5_README.md`](STEP5_README.md).
