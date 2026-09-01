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

## Usage

```bash
# Telemetry only (JSON)
python3 scripts/ask_copilot.py --telemetry-only --scenario cw_degradation

# Full diagnosis with telemetry + RAG
python3 scripts/ask_copilot.py --asset Chiller-03 --scenario cw_degradation \
  "Chiller-03 has elevated anomaly score. What should I investigate?"
```

## Files

- `copilot/data/demo_scenarios.py` — curated telemetry payloads
- `copilot/tools/telemetry.py` — `get_chiller_telemetry()` tool
- `copilot/schemas.py` — `DerivedFlag`, `ChillerTelemetry` models
- `copilot/rag/chain.py` — fetches telemetry before retrieval
- `copilot/prompts.py` — includes telemetry block in the human prompt
