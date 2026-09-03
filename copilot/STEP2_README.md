# Step 2 — RAG Chain with Structured LLM Output

Step 2 adds a **LangChain RAG chain** that retrieves engineering documentation from ChromaDB and produces a **structured troubleshooting diagnosis** using an OpenAI LLM.

Telemetry is added in Step 3. LangGraph routing is added in Step 4. Step 5 exposes the workflow as an HTTP API.

## Dependencies

```bash
pip install -r requirements-copilot.txt
cp .env.copilot.example .env.copilot
```

Retrieval uses the same `EMBEDDING_BACKEND` as Step 1 ingest (`local` or `openai`). See [`STEP1_README.md`](STEP1_README.md).

## Setup

```bash
pip install -r requirements-copilot.txt
cp .env.copilot.example .env.copilot
# Fill in Chroma Cloud credentials AND OPENAI_API_KEY
```

Prerequisite: complete Step 1 ingestion first (`python3 scripts/ingest_documents.py`).

## Architecture

```
Engineer question
    ↓
ChromaDB retriever (Step 1)
    ↓
Format context + source labels
    ↓
ChatOpenAI + structured output (Pydantic)
    ↓
TroubleshootingDiagnosis JSON
```

## LangChain components used

| Component | File | Purpose |
|-----------|------|---------|
| Retriever | `copilot/rag/ingest.py` | `similarity_search` on ChromaDB |
| Prompt template | `copilot/prompts.py` | System + human prompts with grounding rules |
| Chat model | `copilot/rag/chain.py` | `ChatOpenAI` |
| Structured output | `copilot/schemas.py` | `TroubleshootingDiagnosis` Pydantic model |
| LCEL chain | `copilot/rag/chain.py` | `prompt \| structured_llm` |

---

## Testing CLI commands

Use `--linear` on `ask_copilot.py` to run this Step 2 chain directly (Step 4 workflow is the default).

### 1. Retrieval only (no OpenAI cost — validates Step 1 + retriever)

```bash
python3 scripts/ask_copilot.py --retrieve-only "elevated condenser water approach"
python3 scripts/ask_copilot.py --retrieve-only "tower tracking error"
python3 scripts/ask_copilot.py --retrieve-only "chiller anomaly investigation SOP"
```

Equivalent standalone retrieval test from Step 1:

```bash
python3 scripts/test_retrieval.py "elevated condenser water approach"
```

### 2. Full RAG diagnosis (requires `OPENAI_API_KEY`)

```bash
python3 scripts/ask_copilot.py --linear \
  --asset Chiller-03 \
  "Chiller-03 has an elevated anomaly score. What should I investigate?"

python3 scripts/ask_copilot.py --linear \
  --asset Chiller-03 \
  "elevated CW approach to wet bulb temperature"
```

### 3. JSON output (machine-readable diagnosis)

```bash
python3 scripts/ask_copilot.py --linear --json --asset Chiller-03 \
  "elevated CW approach to wet bulb"

python3 scripts/ask_copilot.py --linear --json \
  "What should I check when tower tracking error is high?"
```

### Quick smoke test

```bash
pip install -r requirements-copilot.txt
cp .env.copilot.example .env.copilot   # add OPENAI_API_KEY + Chroma creds
EMBEDDING_BACKEND=local python3 scripts/ingest_documents.py
python3 scripts/ask_copilot.py --retrieve-only "elevated condenser water approach"
python3 scripts/ask_copilot.py --linear --json --asset Chiller-03 \
  "Chiller-03 has an elevated anomaly score. What should I investigate?"
```

### Troubleshooting

| Symptom | Fix |
|---------|-----|
| Empty retrieval results | Re-ingest; confirm `EMBEDDING_BACKEND` matches ingest |
| `EMBEDDING_BACKEND=openai requires OPENAI_API_KEY` | Add key to `.env.copilot` |

---

## Structured output fields

| Field | Description |
|-------|-------------|
| `asset` | Equipment ID |
| `condition` | Summary of the problem |
| `potential_causes` | Ranked likely causes |
| `evidence` | Facts from retrieved docs |
| `recommended_investigation` | Field investigation steps |
| `confidence` | high / medium / low |
| `sources` | Cited manuals/SOPs |
| `escalation_required` | True if evidence insufficient |

## Interview talking points (Step 2)

- "I built a RAG chain — not just chat-with-PDF. Retrieval and generation are separate steps I can evaluate independently."
- "Structured output via Pydantic ensures the response is machine-readable and testable."
- "Grounding rules require the LLM to cite retrieved sources and escalate when evidence is weak."
- "I used LangChain for prompt composition and structured output — not for a single API call I'd use the SDK directly."

## Next step

Step 3: Telemetry tool — see [`STEP3_README.md`](STEP3_README.md).
