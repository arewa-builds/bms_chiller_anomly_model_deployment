"""Pydantic schemas for Step 2 RAG responses."""

from __future__ import annotations

from typing import Literal

from pydantic import BaseModel, Field


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
        description="Specific facts from retrieved documentation supporting the analysis"
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
