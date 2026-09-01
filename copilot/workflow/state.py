"""LangGraph workflow state for the troubleshooting copilot."""

from __future__ import annotations

from typing import Any, Literal, TypedDict

from langchain_core.documents import Document

from copilot.schemas import ChillerTelemetry, TroubleshootingDiagnosis


class CopilotState(TypedDict, total=False):
    """Mutable state passed between LangGraph nodes."""

    question: str
    asset_id: str | None
    scenario: str | None
    top_k: int | None
    telemetry: ChillerTelemetry
    route: Literal["normal", "diagnose", "escalate"]
    triage_reason: str
    context: str
    docs: list[Document]
    diagnosis: TroubleshootingDiagnosis
    escalated: bool
    escalation_reason: str
    workflow_trace: list[str]
