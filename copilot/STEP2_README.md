# Step 2 — RAG Chain with Structured LLM Output

Step 2 adds a **LangChain RAG chain** that retrieves engineering documentation from ChromaDB and produces a **structured troubleshooting diagnosis** using an OpenAI LLM.

No LangGraph yet (Step 4). Telemetry is added in Step 3.

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

## Setup

```bash
pip install -r requirements-copilot.txt
cp .env.copilot.example .env.copilot
# Fill in Chroma Cloud credentials AND OPENAI_API_KEY
```

Prerequisite: complete Step 1 ingestion first (`python3 scripts/ingest_documents.py`).

---

## Testing CLI commands

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
python3 scripts/ask_copilot.py \
  --asset Chiller-03 \
  "Chiller-03 has an elevated anomaly score. What should I investigate?"

python3 scripts/ask_copilot.py \
  --asset Chiller-03 \
  "elevated CW approach to wet bulb temperature"
```

### 3. JSON output (machine-readable diagnosis)

```bash
python3 scripts/ask_copilot.py --json --asset Chiller-03 \
  "elevated CW approach to wet bulb"

python3 scripts/ask_copilot.py --json \
  "What should I check when tower tracking error is high?"
```

### Quick smoke test

```bash
pip install -r requirements-copilot.txt
cp .env.copilot.example .env.copilot   # add OPENAI_API_KEY + Chroma creds
python3 scripts/ingest_documents.py
python3 scripts/ask_copilot.py --retrieve-only "elevated condenser water approach"
python3 scripts/ask_copilot.py --json --asset Chiller-03 \
  "Chiller-03 has an elevated anomaly score. What should I investigate?"
```

---

## Usage

### Retrieve only (no API cost — tests Step 1 + retrieval)

```bash
python3 scripts/ask_copilot.py --retrieve-only "elevated condenser water approach"
```

### Full RAG diagnosis

```bash
python3 scripts/ask_copilot.py \
  --asset Chiller-03 \
  "Chiller-03 has an elevated anomaly score. What should I investigate?"
```

### JSON output

```bash
python3 scripts/ask_copilot.py --json --asset Chiller-03 \
  "elevated CW approach to wet bulb"
```

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

## Next step (not implemented yet)

Step 3: Telemetry tool — bring chiller sensor readings and anomaly scores into the prompt.
