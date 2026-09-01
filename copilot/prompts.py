"""Prompt templates for RAG troubleshooting (Steps 2–3)."""

SYSTEM_PROMPT = """You are a senior BMS / chiller troubleshooting engineer assisting with \
industrial equipment anomaly investigation.

Your job is to help engineers investigate equipment problems using the \
current telemetry snapshot and retrieved engineering documentation provided below.

Rules:
1. Ground every claim in telemetry readings and retrieved documentation. Do not invent sensor values.
2. Reference elevated derived flags explicitly when they support the diagnosis.
3. If evidence is insufficient, set confidence to "low" and escalation_required to true.
4. List only sources that appear in the retrieved context.
5. Use industrial terminology: CHW/CW delta-T, RLA, wet bulb approach, tower tracking error, etc.
6. recommended_investigation must be actionable steps an operator can follow in the field.
7. potential_causes should be ranked most-likely first.
"""


def format_telemetry_block(telemetry: dict) -> str:
    """Format telemetry dict for inclusion in the LLM prompt."""
    lines = [
        f"Asset: {telemetry.get('asset_id', 'unknown')}",
        f"Timestamp: {telemetry.get('timestamp', 'unknown')}",
        f"Scenario: {telemetry.get('scenario', 'unknown')}",
    ]
    if telemetry.get("description"):
        lines.append(f"Description: {telemetry['description']}")

    lines.append("")
    lines.append("Raw sensors:")
    for name, value in telemetry.get("raw_sensors", {}).items():
        lines.append(f"  {name}: {value}")

    lines.append("")
    lines.append("Derived flags (elevated + measured value):")
    for flag_name, flag in telemetry.get("derived_flags", {}).items():
        elevated = flag.get("elevated", False)
        value = flag.get("value")
        lines.append(f"  {flag_name}: elevated={elevated}, value={value}")

    anomaly = telemetry.get("anomaly", {})
    lines.extend(
        [
            "",
            "Anomaly status:",
            f"  decision_score: {anomaly.get('decision_score')}",
            f"  label: {anomaly.get('label')}",
            f"  is_anomaly: {anomaly.get('is_anomaly')}",
        ]
    )
    return "\n".join(lines)


HUMAN_PROMPT = """Engineer question:
{question}

{asset_hint}

{telemetry_block}

Retrieved engineering documentation:
{context}

Produce a structured troubleshooting diagnosis grounded in both telemetry and documentation."""
