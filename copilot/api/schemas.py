"""HTTP request/response schemas for the copilot FastAPI service."""

from __future__ import annotations

from pydantic import BaseModel, Field

from copilot.schemas import ChillerTelemetry, WorkflowResult


class DiagnoseRequest(BaseModel):
    """POST /diagnose body."""

    question: str = Field(description="Engineer troubleshooting question")
    asset_id: str | None = Field(default=None, description="Asset ID, e.g. Chiller-03")
    scenario: str | None = Field(
        default=None,
        description="Demo scenario key (cw_degradation, flow_restriction, normal)",
    )


class ScenariosResponse(BaseModel):
    """GET /scenarios response."""

    scenarios: list[str]


class HealthResponse(BaseModel):
    """GET /health response."""

    status: str
    service: str
    version: str
    chroma_mode: str
    openai_configured: bool


# Re-export workflow models for OpenAPI
__all__ = [
    "ChillerTelemetry",
    "DiagnoseRequest",
    "HealthResponse",
    "ScenariosResponse",
    "WorkflowResult",
]
