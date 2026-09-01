# Step 3 — Telemetry Tool

Adds a `get_chiller_telemetry` tool that returns demo sensor snapshots with **derived flags** before the RAG chain calls the LLM.

## Derived flags format

Each flag returns an elevation status plus the measured value:

```json
"derived_flags": {
  "cw_approach_to_wb_elevated": {"elevated": true, "value": 8, "timestamp": "2026-09-01T14:00:00Z"},
  "flow_imbalance_pct_high": {"elevated": true, "value": 10, "timestamp": "2026-09-01T14:00:00Z"},
  "tower_tracking_error_abs_high": {"elevated": true, "value": 12, "timestamp": "2026-09-01T14:00:00Z"}
}
```

## Demo scenarios

| Key | Description |
|-----|-------------|
| `cw_degradation` | Elevated CW approach, flow imbalance, tower tracking error |
| `flow_restriction` | Low condenser flow with high header imbalance |
| `normal` | Steady-state baseline |

Asset aliases (when `--scenario` is omitted):

- `Chiller-03`, `M126` → `cw_degradation`
- `Chiller-03-normal` → `normal`

---

## Testing CLI commands

Prerequisite: complete Step 1 ingestion and set `OPENAI_API_KEY` in `.env.copilot` for full diagnosis tests.

Use `--linear` to run the Step 3 chain without LangGraph routing (Step 4 is the default).

### 1. Telemetry only (no retrieval, no LLM)

```bash
python3 scripts/ask_copilot.py --telemetry-only --scenario cw_degradation
python3 scripts/ask_copilot.py --telemetry-only --scenario flow_restriction
python3 scripts/ask_copilot.py --telemetry-only --scenario normal
```

Telemetry via asset alias (no `--scenario`):

```bash
python3 scripts/ask_copilot.py --telemetry-only --asset Chiller-03
python3 scripts/ask_copilot.py --telemetry-only --asset Chiller-03-normal
```

### 2. Full diagnosis with telemetry + RAG

```bash
python3 scripts/ask_copilot.py --linear --asset Chiller-03 --scenario cw_degradation \
  "Chiller-03 has elevated anomaly score. What should I investigate?"

python3 scripts/ask_copilot.py --linear --scenario flow_restriction \
  "condenser flow is low and headers are imbalanced — what should I check?"

python3 scripts/ask_copilot.py --linear --scenario normal \
  "confirm this chiller looks healthy"
```

### 3. JSON output (telemetry + diagnosis)

```bash
python3 scripts/ask_copilot.py --telemetry-only --scenario cw_degradation --json

python3 scripts/ask_copilot.py --linear --json --asset Chiller-03 --scenario cw_degradation \
  "elevated CW approach and tower tracking error"
```

### 4. Retrieval-only (Step 1/2 check, no telemetry)

```bash
python3 scripts/ask_copilot.py --retrieve-only "tower tracking error"
```

### Quick smoke test

```bash
pip install -r requirements-copilot.txt
cp .env.copilot.example .env.copilot   # add OPENAI_API_KEY + Chroma creds
python3 scripts/ingest_documents.py
python3 scripts/ask_copilot.py --telemetry-only --scenario cw_degradation
python3 scripts/ask_copilot.py --linear --json --asset Chiller-03 --scenario cw_degradation \
  "Chiller-03 has elevated anomaly score. What should I investigate?"
```

---

## Files

- `copilot/data/demo_scenarios.py` — curated telemetry payloads
- `copilot/tools/telemetry.py` — `get_chiller_telemetry()` tool
- `copilot/schemas.py` — `DerivedFlag`, `ChillerTelemetry` models
- `copilot/rag/chain.py` — fetches telemetry before retrieval
- `copilot/prompts.py` — includes telemetry block in the human prompt

## Next step

Step 4: LangGraph workflow with conditional routing and escalation — see [`STEP4_README.md`](STEP4_README.md).
