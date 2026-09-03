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
python3 scripts/ingest_documents.py
```

---

## Testing CLI commands

### 1. Normal route (no LLM — fastest)

Uses `--scenario normal` to skip retrieval and LLM:

```bash
python3 scripts/ask_copilot.py --scenario normal \
  "confirm chiller health"
```

Expected: `Route: normal`, no escalation, high confidence ack.

### 2. Diagnose route (telemetry + RAG + LLM)

```bash
python3 scripts/ask_copilot.py --scenario cw_degradation \
  "Chiller-03 has elevated anomaly score. What should I investigate?"

python3 scripts/ask_copilot.py --scenario flow_restriction \
  "condenser flow is low — what should I check?"
```

Expected: `Route: diagnose` (or `escalate` if confidence is low).

### 3. JSON output (includes routing metadata)

```bash
python3 scripts/ask_copilot.py --json --scenario cw_degradation \
  "elevated CW approach and tower tracking error"
```

Returns `WorkflowResult` with `route`, `triage_reason`, `escalated`, `telemetry`, and `diagnosis`.

### 4. Compare with Step 3 linear chain

```bash
python3 scripts/ask_copilot.py --linear --scenario cw_degradation \
  "elevated CW approach"
```

The `--linear` flag bypasses LangGraph and uses the Step 3 `troubleshoot()` chain directly.

### Quick smoke test

```bash
pip install -r requirements-copilot.txt
cp .env.copilot.example .env.copilot
python3 scripts/ingest_documents.py

# Normal path — no API key needed
python3 scripts/ask_copilot.py --scenario normal "health check"

# Anomaly path — needs OPENAI_API_KEY
python3 scripts/ask_copilot.py --json --scenario cw_degradation \
  "what should I investigate?"
```

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

Step 6: Live telemetry bridge — see [`ROADMAP.md`](ROADMAP.md).
