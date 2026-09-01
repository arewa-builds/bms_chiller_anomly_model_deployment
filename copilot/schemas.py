"""Pydantic schemas for copilot RAG and telemetry responses."""

from __future__ import annotations

from typing import Literal

from pydantic import BaseModel, Field


class DerivedFlag(BaseModel):
    """A derived diagnostic flag with measured value and elevation status."""

    elevated: bool = Field(description="True when the value exceeds the alert threshold")
    value: float = Field(description="Measured value for this diagnostic indicator")


class AnomalyStatus(BaseModel):
    """LOF model anomaly score for the current reading."""

    is_anomaly: bool
    decision_score: float
    label: int


class ChillerTelemetry(BaseModel):
    """Live (or demo) chiller sensor snapshot for the troubleshooting copilot."""

    asset_id: str
    scenario: str
    timestamp: str
    description: str | None = None
    anomaly: AnomalyStatus
    raw_sensors: dict[str, float]
    derived_flags: dict[str, DerivedFlag]


class SourceCitation(BaseModel):
    """A document source cited in the diagnosis."""

    title: str = Field(description="Document name or manual title")
    section: str | None = Field(
        default=None, description="Section or heading if identifiable"
    )


class TroubleshootingDiagnosis(BaseModel):
    """Structured troubleshooting response grounded in retrieved documentation."""

    asset: str = Field(
        description="Equipment asset identifier, e.g. Chiller-03 or M126"
    )
    condition: str = Field(
        description="Brief summary of the observed or reported condition"
    )
    potential_causes: list[str] = Field(
        description="Ranked list of likely causes based on evidence"
    )
    evidence: list[str] = Field(
        description="Specific facts from retrieved documentation and telemetry"
    )
    recommended_investigation: list[str] = Field(
        description="Ordered investigation steps for the engineer"
    )
    confidence: Literal["high", "medium", "low"] = Field(
        description="Confidence in the diagnosis given available evidence"
    )
    sources: list[SourceCitation] = Field(
        description="Documentation sources used; must match retrieved context"
    )
    escalation_required: bool = Field(
        default=False,
        description="True if evidence is insufficient and a senior engineer should review",
    )
