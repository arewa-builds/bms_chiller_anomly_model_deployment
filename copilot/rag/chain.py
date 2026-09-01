"""
RAG chain: telemetry + retrieve documentation + LLM structured diagnosis.

For LangGraph routing and escalation, see ``copilot.workflow.graph`` (Step 4).
"""

from __future__ import annotations

from langchain_core.documents import Document
from langchain_core.prompts import ChatPromptTemplate
from langchain_openai import ChatOpenAI

from copilot.config import OPENAI_API_KEY, OPENAI_MODEL, RETRIEVAL_TOP_K
from copilot.prompts import HUMAN_PROMPT, SYSTEM_PROMPT, format_telemetry_block
from copilot.rag.ingest import retrieve
from copilot.schemas import ChillerTelemetry, SourceCitation, TroubleshootingDiagnosis
from copilot.tools.telemetry import get_chiller_telemetry


def _require_openai_key() -> None:
    if not OPENAI_API_KEY or OPENAI_API_KEY.startswith("sk-your"):
        raise ValueError(
            "OPENAI_API_KEY is missing or still a placeholder. "
            "Add it to .env.copilot (see .env.copilot.example)."
        )


def format_retrieved_context(docs: list[Document]) -> str:
    """Format retrieved chunks with source labels for the LLM prompt."""
    if not docs:
        return "(No relevant documentation retrieved.)"

    parts: list[str] = []
    for i, doc in enumerate(docs, 1):
        meta = doc.metadata or {}
        filename = meta.get("filename", meta.get("source", f"chunk_{i}"))
        doc_type = meta.get("document_type", meta.get("doc_type", ""))
        header = f"[Source {i}: {filename}"
        if doc_type:
            header += f" | {doc_type}"
        header += "]"
        parts.append(f"{header}\n{doc.page_content.strip()}")
    return "\n\n---\n\n".join(parts)


def extract_sources_from_docs(docs: list[Document]) -> list[SourceCitation]:
    """Build source list from retrieved document metadata."""
    seen: set[str] = set()
    sources: list[SourceCitation] = []
    for doc in docs:
        meta = doc.metadata or {}
        filename = meta.get("filename", "unknown")
        if filename in seen:
            continue
        seen.add(filename)
        doc_type = meta.get("document_type", meta.get("doc_type"))
        sources.append(SourceCitation(title=filename, section=doc_type))
    return sources


def retrieve_context(question: str, top_k: int | None = None) -> tuple[str, list[Document]]:
    """Retrieve docs and return formatted context + raw documents."""
    k = top_k or RETRIEVAL_TOP_K
    docs = retrieve(question, top_k=k)
    return format_retrieved_context(docs), docs


def build_chain():
    """Build the LangChain RAG chain with structured output."""
    _require_openai_key()

    prompt = ChatPromptTemplate.from_messages(
        [("system", SYSTEM_PROMPT), ("human", HUMAN_PROMPT)]
    )
    llm = ChatOpenAI(model=OPENAI_MODEL, temperature=0)
    structured_llm = llm.with_structured_output(TroubleshootingDiagnosis)
    return prompt | structured_llm


def fetch_telemetry(
    asset_id: str | None = None,
    scenario: str | None = None,
) -> ChillerTelemetry:
    """Fetch demo telemetry for the given asset and scenario."""
    resolved_asset = asset_id or "Chiller-03"
    return get_chiller_telemetry(resolved_asset, scenario=scenario)


def troubleshoot(
    question: str,
    *,
    asset_id: str | None = None,
    top_k: int | None = None,
    scenario: str | None = None,
    include_telemetry: bool = True,
) -> TroubleshootingDiagnosis:
    """
    Run the full RAG troubleshooting pipeline.

    1. Fetch current telemetry (demo scenarios)
    2. Retrieve relevant documentation from ChromaDB
    3. Format context with source labels
    4. Call LLM with structured output schema
    """
    telemetry: ChillerTelemetry | None = None
    telemetry_block = "(No telemetry provided.)"
    if include_telemetry:
        telemetry = fetch_telemetry(asset_id=asset_id, scenario=scenario)
        telemetry_block = "Current telemetry:\n" + format_telemetry_block(
            telemetry.model_dump()
        )

    context, docs = retrieve_context(question, top_k=top_k)

    asset_hint = ""
    resolved_asset = asset_id or (telemetry.asset_id if telemetry else None)
    if resolved_asset:
        asset_hint = f"Asset context: {resolved_asset}"

    chain = build_chain()
    diagnosis: TroubleshootingDiagnosis = chain.invoke(
        {
            "question": question,
            "asset_hint": asset_hint,
            "telemetry_block": telemetry_block,
            "context": context,
        }
    )

    # Ensure retrieved sources are available even if LLM omits some
    if not diagnosis.sources and docs:
        diagnosis.sources = extract_sources_from_docs(docs)

    return diagnosis
