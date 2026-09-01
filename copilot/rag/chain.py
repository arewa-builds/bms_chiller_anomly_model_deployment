"""
Step 2 — RAG chain: retrieve documentation + LLM structured diagnosis.

No telemetry tool yet (Step 3). No LangGraph yet (Step 4).
"""

from __future__ import annotations

from langchain_core.documents import Document
from langchain_core.prompts import ChatPromptTemplate
from langchain_openai import ChatOpenAI

from copilot.config import OPENAI_API_KEY, OPENAI_MODEL, RETRIEVAL_TOP_K
from copilot.prompts import HUMAN_PROMPT, SYSTEM_PROMPT
from copilot.rag.ingest import retrieve
from copilot.schemas import SourceCitation, TroubleshootingDiagnosis


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


def troubleshoot(
    question: str,
    *,
    asset_id: str | None = None,
    top_k: int | None = None,
) -> TroubleshootingDiagnosis:
    """
    Run the full RAG troubleshooting pipeline.

    1. Retrieve relevant documentation from ChromaDB
    2. Format context with source labels
    3. Call LLM with structured output schema
    """
    context, docs = retrieve_context(question, top_k=top_k)

    asset_hint = ""
    if asset_id:
        asset_hint = f"Asset context: {asset_id}"

    chain = build_chain()
    diagnosis: TroubleshootingDiagnosis = chain.invoke(
        {
            "question": question,
            "asset_hint": asset_hint,
            "context": context,
        }
    )

    # Ensure retrieved sources are available even if LLM omits some
    if not diagnosis.sources and docs:
        diagnosis.sources = extract_sources_from_docs(docs)

    return diagnosis
