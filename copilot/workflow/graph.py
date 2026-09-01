"""
Step 4 — LangGraph workflow with conditional routing and escalation.

Flow:
  fetch_telemetry → triage → normal_ack | retrieve → diagnose → escalate? → END
"""

from __future__ import annotations

from langgraph.graph import END, START, StateGraph

from copilot.prompts import format_telemetry_block
from copilot.rag.chain import (
    build_chain,
    extract_sources_from_docs,
    fetch_telemetry,
    format_retrieved_context,
    retrieve_context,
)
from copilot.schemas import (
    ChillerTelemetry,
    SourceCitation,
    TroubleshootingDiagnosis,
    WorkflowResult,
)
from copilot.workflow.state import CopilotState
from copilot.workflow.triage import (
    should_escalate_after_diagnosis,
    triage_telemetry,
)


def _trace(state: CopilotState, message: str) -> list[str]:
    trace = list(state.get("workflow_trace", []))
    trace.append(message)
    return trace


def node_fetch_telemetry(state: CopilotState) -> dict:
    asset_id = state.get("asset_id")
    scenario = state.get("scenario")
    telemetry = fetch_telemetry(asset_id=asset_id, scenario=scenario)
    return {
        "telemetry": telemetry,
        "workflow_trace": _trace(state, "fetch_telemetry"),
    }


def node_triage(state: CopilotState) -> dict:
    telemetry: ChillerTelemetry = state["telemetry"]
    route, reason = triage_telemetry(telemetry)
    return {
        "route": route,
        "triage_reason": reason,
        "workflow_trace": _trace(state, f"triage → {route}"),
    }


def route_after_triage(state: CopilotState) -> str:
    return state.get("route", "diagnose")


def node_normal_ack(state: CopilotState) -> dict:
    telemetry: ChillerTelemetry = state["telemetry"]
    diagnosis = TroubleshootingDiagnosis(
        asset=telemetry.asset_id,
        condition="Normal steady-state operation — no active fault indicators",
        potential_causes=["Equipment operating within expected parameters"],
        evidence=[
            f"LOF decision_score={telemetry.anomaly.decision_score} (normal)",
            "No elevated derived flags",
            f"Reading timestamp: {telemetry.timestamp}",
        ],
        recommended_investigation=[
            "Continue routine monitoring",
            "No field investigation required at this time",
        ],
        confidence="high",
        sources=[],
        escalation_required=False,
    )
    return {
        "diagnosis": diagnosis,
        "escalated": False,
        "workflow_trace": _trace(state, "normal_ack"),
    }


def node_retrieve(state: CopilotState) -> dict:
    question = state["question"]
    top_k = state.get("top_k")
    context, docs = retrieve_context(question, top_k=top_k)
    return {
        "context": context,
        "docs": docs,
        "workflow_trace": _trace(state, f"retrieve ({len(docs)} chunks)"),
    }


def node_diagnose(state: CopilotState) -> dict:
    telemetry: ChillerTelemetry = state["telemetry"]
    question = state["question"]
    context = state.get("context", "")
    docs = state.get("docs", [])

    asset_hint = f"Asset context: {telemetry.asset_id}"
    telemetry_block = "Current telemetry:\n" + format_telemetry_block(
        telemetry.model_dump()
    )

    chain = build_chain()
    diagnosis: TroubleshootingDiagnosis = chain.invoke(
        {
            "question": question,
            "asset_hint": asset_hint,
            "telemetry_block": telemetry_block,
            "context": context,
        }
    )

    if not diagnosis.sources and docs:
        diagnosis.sources = extract_sources_from_docs(docs)

    return {
        "diagnosis": diagnosis,
        "route": "diagnose",
        "workflow_trace": _trace(state, "diagnose"),
    }


def route_after_diagnose(state: CopilotState) -> str:
    diagnosis = state.get("diagnosis")
    docs = state.get("docs", [])
    if diagnosis is None:
        return "escalate"

    escalate, _ = should_escalate_after_diagnosis(
        confidence=diagnosis.confidence,
        escalation_required=diagnosis.escalation_required,
        docs_retrieved=len(docs),
    )
    return "escalate" if escalate else "done"


def node_escalate(state: CopilotState) -> dict:
    diagnosis: TroubleshootingDiagnosis = state["diagnosis"]
    docs = state.get("docs", [])

    escalate, reason = should_escalate_after_diagnosis(
        confidence=diagnosis.confidence,
        escalation_required=diagnosis.escalation_required,
        docs_retrieved=len(docs),
    )
    if not escalate and not diagnosis.escalation_required:
        reason = "Forced escalation review"

    escalation_steps = [
        "ESCALATE: Notify senior maintenance or controls engineer",
        "Document anomaly decision_score, elevated flags, and field observations",
        "Review 7-day baseline trends before returning equipment to full load",
    ]

    updated = diagnosis.model_copy(
        update={
            "escalation_required": True,
            "confidence": "low" if diagnosis.confidence == "high" else diagnosis.confidence,
            "recommended_investigation": escalation_steps
            + [s for s in diagnosis.recommended_investigation if not s.startswith("ESCALATE:")],
        }
    )

    return {
        "diagnosis": updated,
        "route": "escalate",
        "escalated": True,
        "escalation_reason": reason,
        "workflow_trace": _trace(state, f"escalate ({reason})"),
    }


def build_workflow():
    """Compile the LangGraph troubleshooting workflow."""
    graph = StateGraph(CopilotState)

    graph.add_node("fetch_telemetry", node_fetch_telemetry)
    graph.add_node("triage", node_triage)
    graph.add_node("normal_ack", node_normal_ack)
    graph.add_node("retrieve", node_retrieve)
    graph.add_node("diagnose", node_diagnose)
    graph.add_node("escalate", node_escalate)

    graph.add_edge(START, "fetch_telemetry")
    graph.add_edge("fetch_telemetry", "triage")
    graph.add_conditional_edges(
        "triage",
        route_after_triage,
        {"normal": "normal_ack", "diagnose": "retrieve"},
    )
    graph.add_edge("normal_ack", END)
    graph.add_edge("retrieve", "diagnose")
    graph.add_conditional_edges(
        "diagnose",
        route_after_diagnose,
        {"escalate": "escalate", "done": END},
    )
    graph.add_edge("escalate", END)

    return graph.compile()


def run_workflow(
    question: str,
    *,
    asset_id: str | None = None,
    scenario: str | None = None,
    top_k: int | None = None,
) -> WorkflowResult:
    """Execute the LangGraph copilot workflow and return structured output."""
    app = build_workflow()
    final_state = app.invoke(
        {
            "question": question,
            "asset_id": asset_id,
            "scenario": scenario,
            "top_k": top_k,
            "workflow_trace": [],
        }
    )

    telemetry: ChillerTelemetry = final_state["telemetry"]
    diagnosis: TroubleshootingDiagnosis = final_state["diagnosis"]
    route = final_state.get("route", "diagnose")
    if route == "normal":
        route = "normal"
    elif final_state.get("escalated"):
        route = "escalate"

    return WorkflowResult(
        route=route,
        triage_reason=final_state.get("triage_reason", ""),
        escalated=bool(final_state.get("escalated")),
        telemetry=telemetry,
        diagnosis=diagnosis,
    )
