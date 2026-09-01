"""Telemetry triage rules for LangGraph routing (Step 4)."""

from __future__ import annotations

from copilot.schemas import ChillerTelemetry


def elevated_flag_names(telemetry: ChillerTelemetry) -> list[str]:
    """Return names of derived flags currently elevated."""
    return [
        name
        for name, flag in telemetry.derived_flags.items()
        if flag.elevated
    ]


def triage_telemetry(telemetry: ChillerTelemetry) -> tuple[str, str]:
    """
    Decide the initial workflow route from telemetry.

    Returns:
        (route, reason) where route is ``normal`` or ``diagnose``.
    """
    elevated = elevated_flag_names(telemetry)

    if (
        not telemetry.anomaly.is_anomaly
        and not elevated
        and telemetry.scenario == "normal"
    ):
        return (
            "normal",
            "No LOF anomaly and no elevated derived flags — steady-state operation",
        )

    if telemetry.anomaly.is_anomaly:
        if elevated:
            return (
                "diagnose",
                f"LOF anomaly with elevated flags: {', '.join(elevated)}",
            )
        return "diagnose", "LOF model flagged anomaly"

    if elevated:
        return "diagnose", f"Elevated derived flags without LOF anomaly: {', '.join(elevated)}"

    return "normal", "Telemetry within normal operating bounds"


def should_escalate_after_diagnosis(
    *,
    confidence: str,
    escalation_required: bool,
    docs_retrieved: int,
) -> tuple[bool, str]:
    """
    Post-diagnosis escalation check.

    Returns:
        (escalate, reason)
    """
    if docs_retrieved == 0:
        return True, "No relevant documentation retrieved"

    if escalation_required:
        return True, "LLM marked escalation_required"

    if confidence == "low":
        return True, "LLM confidence is low"

    return False, ""
